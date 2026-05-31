"""ترحيل أوامر التصنيع من البنية القديمة إلى الجديدة (Pre).

يُحفظ هنا قبل تعديل البنية:
- بيانات أمر التصنيع (المنتج/الكمية/القسم/حقول الاعتماد...) لكل WO قديم.
- بنود المواد القديمة (rwasi_work_order_material).
- ربط بنود التنفيذ بأمر التصنيع (rwasi_work_order_line.order_id).
- ربط purchase.order.workshop_order_id لإعادة توجيهه لطلب المواد الجديد.

ثم يأخذ post-migration هذه البيانات وينشئ:
- WorkOrderJob لكل WO قديم.
- MaterialRequest يحوي بنود المواد + حالة الاعتماد.
- يربط بنود التنفيذ والـ POs بالكيانات الجديدة.
"""


def migrate(cr, version):
    if not version:
        return  # تثبيت جديد — لا حاجة للترحيل

    # تأكد من وجود البنية القديمة (إن لم توجد فقد تم الترحيل سابقاً)
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rwasi_work_order' AND column_name = 'product_id'
    """)
    if not cr.fetchone():
        return

    # ١) حفظ بيانات أوامر التصنيع القديمة (بكل حقول المنتج والاعتماد)
    cr.execute("DROP TABLE IF EXISTS _rwasi_mig_wo")
    cr.execute("""
        CREATE TABLE _rwasi_mig_wo AS
        SELECT id AS old_id,
               sale_line_id,
               product_id,
               product_qty,
               workshop_scope,
               material_approval_state,
               material_approver_assignee_id,
               material_approver_id,
               finance_user_id,
               finance_approver_id,
               finance_approval_date,
               purchase_user_id,
               material_handover_done,
               material_handover_date,
               material_received_by,
               material_handover_signature,
               material_approval_reason
        FROM rwasi_work_order
    """)

    # ٢) حفظ بنود المواد القديمة (إن وُجد الجدول)
    cr.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'rwasi_work_order_material'
    """)
    if cr.fetchone():
        cr.execute("DROP TABLE IF EXISTS _rwasi_mig_mat")
        cr.execute("""
            CREATE TABLE _rwasi_mig_mat AS
            SELECT id AS old_line_id, order_id, material_id, vendor_id, qty_needed
            FROM rwasi_work_order_material
        """)

    # ٣) ربط بنود التنفيذ بأمر التصنيع القديم (لإعادة التوجيه لأمر العمل)
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rwasi_work_order_line' AND column_name = 'order_id'
    """)
    if cr.fetchone():
        cr.execute("DROP TABLE IF EXISTS _rwasi_mig_exec")
        cr.execute("""
            CREATE TABLE _rwasi_mig_exec AS
            SELECT id AS line_id, order_id
            FROM rwasi_work_order_line
        """)

    # ٤) ربط purchase.order بأمر التصنيع القديم
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_order' AND column_name = 'workshop_order_id'
    """)
    if cr.fetchone():
        cr.execute("DROP TABLE IF EXISTS _rwasi_mig_po")
        cr.execute("""
            CREATE TABLE _rwasi_mig_po AS
            SELECT id AS po_id, workshop_order_id
            FROM purchase_order
            WHERE workshop_order_id IS NOT NULL
        """)
