"""ترحيل أوامر التصنيع من البنية القديمة إلى الجديدة (Post).

يقرأ البيانات المحفوظة في pre-migration ويبني:
- WorkOrderJob لكل أمر تصنيع قديم (من المنتج/الكمية/القسم).
- MaterialRequest يحوي بنود المواد القديمة + حالة الاعتماد.
- يُعيد توجيه بنود التنفيذ من order_id إلى job_id.
- يربط purchase.order بطلب المواد بدل أمر التصنيع.
"""

from odoo import api, SUPERUSER_ID


# تطابق حالات الاعتماد القديمة مع الجديدة
_STATE_MAP = {
    'draft': 'draft',
    'to_approve': 'to_approve',
    'to_finance': 'to_finance',
    'approved': 'approved',
    'rejected': 'rejected',
    'to_revise': 'to_revise',
}


def _table_exists(cr, name):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (name,))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return
    if not _table_exists(cr, '_rwasi_mig_wo'):
        return  # لا بيانات للترحيل (تثبيت جديد أو ترحيل سابق)

    env = api.Environment(cr, SUPERUSER_ID, {})

    # ============ ١) إنشاء WorkOrderJob لكل WO قديم ============
    cr.execute("""
        SELECT old_id, sale_line_id, product_id, product_qty, workshop_scope
        FROM _rwasi_mig_wo
    """)
    wo_to_job = {}  # old_wo_id → new job_id
    Job = env['rwasi.work.job'].sudo().with_context(tracking_disable=True)
    for old_id, sale_line_id, product_id, qty, scope in cr.fetchall():
        if not product_id:
            continue  # WO قديم بلا منتج — يُترك كما هو
        job = Job.create({
            'work_order_id': old_id,
            'sale_line_id': sale_line_id,
            'product_id': product_id,
            'product_qty': qty or 1.0,
            'workshop_scope': scope,
        })
        wo_to_job[old_id] = job.id

    # ============ ٢) إعادة ربط بنود التنفيذ ============
    if _table_exists(cr, '_rwasi_mig_exec'):
        cr.execute("SELECT line_id, order_id FROM _rwasi_mig_exec")
        for line_id, old_order_id in cr.fetchall():
            new_job_id = wo_to_job.get(old_order_id)
            if new_job_id:
                cr.execute(
                    "UPDATE rwasi_work_order_line SET job_id = %s WHERE id = %s",
                    (new_job_id, line_id))
            else:
                # بند يتيم بلا job — احذفه لتجنب كسر قيد NOT NULL
                cr.execute(
                    "DELETE FROM rwasi_work_order_line WHERE id = %s",
                    (line_id,))

    # ============ ٣) إنشاء MaterialRequest لكل WO قديم ============
    cr.execute("""
        SELECT old_id, material_approval_state, material_approver_assignee_id,
               material_approver_id, finance_user_id, finance_approver_id,
               finance_approval_date, purchase_user_id, material_handover_done,
               material_handover_date, material_received_by,
               material_handover_signature, material_approval_reason
        FROM _rwasi_mig_wo
    """)
    wo_to_request = {}  # old_wo_id → new request_id
    Request = env['rwasi.material.request'].sudo().with_context(tracking_disable=True)
    for row in cr.fetchall():
        (old_id, old_state, mat_assignee, mat_approver, fin_user, fin_approver,
         fin_date, pur_user, handover_done, handover_date,
         received_by, sig, reason) = row
        job_id = wo_to_job.get(old_id)
        if not job_id:
            continue
        new_state = 'handover_done' if handover_done else (
            _STATE_MAP.get(old_state) or 'draft')
        vals = {
            'work_order_id': old_id,
            'work_job_id': job_id,
            'reason': 'initial',
            'state': new_state,
            'material_approver_assignee_id': mat_assignee,
            'material_approver_id': mat_approver,
            'finance_user_id': fin_user,
            'finance_approver_id': fin_approver,
            'finance_approval_date': fin_date,
            'purchase_user_id': pur_user,
            'material_handover_done': bool(handover_done),
            'material_handover_date': handover_date,
            'material_received_by': received_by,
            'material_handover_signature': sig,
            'approval_reason': reason,
        }
        # حذف القيم الفارغة لتفادي إقحام None في حقول M2O
        vals = {k: v for k, v in vals.items() if v is not None}
        req = Request.create(vals)
        wo_to_request[old_id] = req.id

    # ============ ٤) إنشاء بنود طلب المواد ============
    if _table_exists(cr, '_rwasi_mig_mat'):
        cr.execute("""
            SELECT order_id, material_id, vendor_id, qty_needed
            FROM _rwasi_mig_mat
        """)
        Line = env['rwasi.material.request.line'].sudo()
        for old_order_id, material_id, vendor_id, qty in cr.fetchall():
            req_id = wo_to_request.get(old_order_id)
            if not req_id or not material_id:
                continue
            line_vals = {
                'request_id': req_id,
                'material_id': material_id,
                'qty_needed': qty or 1.0,
            }
            if vendor_id:
                line_vals['vendor_id'] = vendor_id
            Line.create(line_vals)

    # ============ ٥) ربط purchase.order بـ material_request ============
    if _table_exists(cr, '_rwasi_mig_po'):
        cr.execute("SELECT po_id, workshop_order_id FROM _rwasi_mig_po")
        PO = env['purchase.order'].sudo()
        for po_id, old_wo_id in cr.fetchall():
            req_id = wo_to_request.get(old_wo_id)
            if req_id:
                # write() حتى يُعاد حساب workshop_order_id (stored related)
                PO.browse(po_id).write({'material_request_id': req_id})

    # ============ ٦) تنظيف الجداول المؤقتة ============
    for tbl in ('_rwasi_mig_wo', '_rwasi_mig_mat',
                '_rwasi_mig_exec', '_rwasi_mig_po'):
        cr.execute(f"DROP TABLE IF EXISTS {tbl}")
