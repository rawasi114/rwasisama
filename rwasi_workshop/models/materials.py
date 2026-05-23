from odoo import models, fields


# ============================================================
# RS-WS-02 — طلب مواد (Material Requisition)
# ============================================================
class MaterialRequisition(models.Model):
    _name = 'rwasi.material.requisition'
    _description = 'طلب مواد (RS-WS-02)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.material.requisition'

    work_order_id = fields.Many2one(
        'rwasi.work.order', string='رقم أمر التشغيل', ondelete='set null')
    requesting_dept = fields.Char(string='القسم الطالب')
    request_date = fields.Date(
        string='تاريخ الطلب', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.material.requisition.line', 'requisition_id', string='المواد المطلوبة')

    # سبب الطلب
    just_work_order = fields.Boolean(string='تنفيذ أمر تشغيل')
    just_replenishment = fields.Boolean(string='تعويض مخزون')
    just_maintenance = fields.Boolean(string='صيانة')
    just_sample = fields.Boolean(string='عينة / تجريب')
    just_emergency = fields.Boolean(string='طلب طارئ')


class MaterialRequisitionLine(models.Model):
    _name = 'rwasi.material.requisition.line'
    _description = 'بند طلب مواد'
    _order = 'sequence, id'

    requisition_id = fields.Many2one(
        'rwasi.material.requisition', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    code = fields.Char(string='رقم الصنف')
    description = fields.Char(string='وصف المادة', required=True)
    spec = fields.Char(string='المواصفة')
    qty = fields.Float(string='الكمية', default=1.0)
    uom = fields.Char(string='الوحدة')
    need_by = fields.Date(string='تاريخ الحاجة')


# ============================================================
# RS-WS-03 — استلام مواد من المستودع (Goods Received Note)
# ============================================================
class MaterialReceipt(models.Model):
    _name = 'rwasi.material.receipt'
    _description = 'استلام مواد من المستودع (RS-WS-03)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.material.receipt'

    work_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التشغيل', ondelete='set null')
    supplier_id = fields.Many2one('res.partner', string='المورّد')
    po_number = fields.Char(string='رقم أمر الشراء')
    invoice_no = fields.Char(string='رقم الفاتورة')
    received_on = fields.Date(
        string='تاريخ الاستلام', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.material.receipt.line', 'receipt_id', string='بنود الاستلام')

    # حالة الاستلام والفحص الظاهري
    insp_conforming = fields.Boolean(string='مطابق للمواصفات')
    insp_conditional = fields.Boolean(string='قبول مشروط')
    insp_rejected = fields.Boolean(string='مرفوض')
    insp_damaged = fields.Boolean(string='تالف بالنقل')
    insp_short_qty = fields.Boolean(string='نقص بالكمية')
    insp_over_qty = fields.Boolean(string='فائض')
    insp_coc_attached = fields.Boolean(string='شهادة منشأ مرفقة')
    insp_lab_cert = fields.Boolean(string='شهادة فحص مختبر')
    insp_mtc_sheet = fields.Boolean(string='بطاقة مادة (MTC)')
    inspection_notes = fields.Text(string='ملاحظات الفحص')

    # كتل التوقيع الخاصة (أمين المستودع / مهندس الجودة)
    storekeeper_id_no = fields.Char(string='رقم بصمة أمين المستودع')
    qc_ref = fields.Char(string='رقم الفحص (QC)')


class MaterialReceiptLine(models.Model):
    _name = 'rwasi.material.receipt.line'
    _description = 'بند استلام مواد'
    _order = 'sequence, id'

    receipt_id = fields.Many2one(
        'rwasi.material.receipt', required=True, ondelete='cascade')
    sequence = fields.Integer(string='#', default=10)
    item_code = fields.Char(string='كود الصنف')
    description = fields.Char(string='الوصف', required=True)
    po_qty = fields.Float(string='الكمية المطلوبة')
    recv_qty = fields.Float(string='الكمية المستلمة')
    uom = fields.Char(string='الوحدة')
    conformance = fields.Selection([
        ('conforming', 'مطابق'),
        ('conditional', 'قبول مشروط'),
        ('rejected', 'مرفوض'),
    ], string='حالة المطابقة')


# ============================================================
# RS-WS-04 — صرف مواد للورشة (Material Issue Voucher)
# ============================================================
class MaterialIssue(models.Model):
    _name = 'rwasi.material.issue'
    _description = 'صرف مواد للورشة (RS-WS-04)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.material.issue'

    requisition_id = fields.Many2one(
        'rwasi.material.requisition', string='مرجع طلب المواد')
    workshop = fields.Char(string='قسم الورشة المستلم')
    receiver = fields.Char(string='المستلم')
    issue_date = fields.Date(
        string='تاريخ الصرف', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.material.issue.line', 'issue_id', string='المواد المنصرفة')

    # تخصيص التكلفة
    project_no = fields.Char(string='رقم المشروع')
    cost_center = fields.Char(string='مركز التكلفة')
    boq_item = fields.Char(string='رقم البند')
    job_no = fields.Char(string='رقم العمل')

    receiver_id_no = fields.Char(string='رقم بصمة المستلم')


class MaterialIssueLine(models.Model):
    _name = 'rwasi.material.issue.line'
    _description = 'بند صرف مواد'
    _order = 'sequence, id'

    issue_id = fields.Many2one(
        'rwasi.material.issue', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    item_code = fields.Char(string='كود الصنف')
    description = fields.Char(string='الوصف', required=True)
    uom = fields.Char(string='الوحدة')
    issued = fields.Float(string='المنصرف')
    returned = fields.Float(string='المرتجع')
    net = fields.Float(string='الصافي')
    bin_card = fields.Char(string='رقم البطاقة')


# ============================================================
# RS-WS-21 — طلب مواد (Material Request مرتبط بأمر البيع)
# ============================================================
class MaterialRequest(models.Model):
    _name = 'rwasi.material.request'
    _description = 'طلب مواد - مرتبط بأمر البيع (RS-WS-21)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.material.request'

    requested_by = fields.Char(string='الجهة الطالبة')
    related_so_id = fields.Many2one('sale.order', string='أمر البيع المرتبط')
    work_order_id = fields.Many2one('rwasi.work.order', string='أمر التشغيل')
    request_date = fields.Date(
        string='التاريخ', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.material.request.line', 'request_id', string='المواد المطلوبة')

    # سبب الطلب
    just_project = fields.Boolean(string='تنفيذ مشروع')
    just_replenishment = fields.Boolean(string='تعويض مخزون')
    just_maintenance = fields.Boolean(string='صيانة')
    just_emergency = fields.Boolean(string='طلب طارئ')

    # كتل اعتماد خاصة (طالب الصرف / المراجع المالي / معتمد من الإدارة)
    finance_name = fields.Char(string='المراجع المالي - الاسم')
    finance_date = fields.Date(string='المراجع المالي - التاريخ')
    finance_signature = fields.Binary(string='المراجع المالي - التوقيع')


class MaterialRequestLine(models.Model):
    _name = 'rwasi.material.request.line'
    _description = 'بند طلب مواد مرتبط بأمر البيع'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'rwasi.material.request', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    so_item_ref = fields.Char(string='رقم البند المرتبط (SO Item)')
    description = fields.Char(string='وصف المادة', required=True)
    spec = fields.Char(string='المواصفة')
    qty = fields.Float(string='الكمية', default=1.0)
    uom = fields.Char(string='الوحدة')
    need_by = fields.Date(string='تاريخ الحاجة')
    notes = fields.Char(string='ملاحظات')
