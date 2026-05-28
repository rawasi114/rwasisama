from odoo import models, fields


# ============================================================
# RS-WS-15 — تقرير فحص الجودة (QC Inspection Report)
# ============================================================
class QcInspection(models.Model):
    _name = 'rwasi.qc.inspection'
    _description = 'تقرير فحص الجودة (RS-WS-15)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.qc.inspection'

    item_inspected = fields.Char(string='العنصر المفحوص')
    work_order_id = fields.Many2one('rwasi.work.order', string='رقم أمر التشغيل')
    inspection_date = fields.Date(
        string='تاريخ الفحص', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.qc.inspection.line', 'inspection_id', string='قائمة الفحص')

    # القرار النهائي
    disposition = fields.Selection([
        ('accept', 'قبول كامل'),
        ('accept_notes', 'قبول مع ملاحظات'),
        ('rework', 'إعادة عمل'),
        ('reject', 'رفض'),
    ], string='القرار النهائي')
    non_conformity = fields.Text(string='تفاصيل عدم المطابقة')

    # المفتش الفني
    inspector_name = fields.Char(string='المفتش الفني - الاسم')
    inspector_date = fields.Date(string='المفتش الفني - التاريخ')
    inspector_signature = fields.Binary(string='المفتش الفني - التوقيع')
    inspector_cert = fields.Char(string='رقم الشهادة')


class QcInspectionLine(models.Model):
    _name = 'rwasi.qc.inspection.line'
    _description = 'بند فحص جودة'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'rwasi.qc.inspection', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    check_item = fields.Char(string='بند الفحص', required=True)
    acceptance = fields.Char(string='المعيار')
    actual = fields.Char(string='القراءة الفعلية')
    result = fields.Selection([
        ('pass', 'يطابق'),
        ('fail', 'لا يطابق'),
    ], string='النتيجة')
    remark = fields.Char(string='ملاحظة')


# ============================================================
# RS-WS-16 — تقرير عدم المطابقة (NCR)
# ============================================================
class Ncr(models.Model):
    _name = 'rwasi.ncr'
    _description = 'تقرير عدم المطابقة - NCR (RS-WS-16)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.ncr'

    item = fields.Char(string='العنصر / البند')
    detected_on = fields.Date(
        string='تاريخ الرصد', default=fields.Date.context_today)
    description = fields.Text(string='وصف عدم المطابقة')

    # التصنيف
    cls_major = fields.Boolean(string='كبرى')
    cls_minor = fields.Boolean(string='صغرى')
    cls_observation = fields.Boolean(string='ملاحظة')
    cls_repeated = fields.Boolean(string='متكررة')

    root_cause = fields.Text(string='تحليل السبب الجذري')
    action_ids = fields.One2many(
        'rwasi.ncr.action', 'ncr_id', string='الإجراء التصحيحي والوقائي')

    # رصد عدم المطابقة / مدير الجودة
    raised_name = fields.Char(string='رصد عدم المطابقة - الاسم')
    raised_date = fields.Date(string='رصد عدم المطابقة - التاريخ')
    raised_signature = fields.Binary(string='رصد عدم المطابقة - التوقيع')
    qa_manager_name = fields.Char(string='مدير الجودة - الاسم')
    qa_manager_date = fields.Date(string='مدير الجودة - التاريخ')
    qa_manager_signature = fields.Binary(string='مدير الجودة - التوقيع')


class NcrAction(models.Model):
    _name = 'rwasi.ncr.action'
    _description = 'إجراء تصحيحي/وقائي'
    _order = 'sequence, id'

    ncr_id = fields.Many2one('rwasi.ncr', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    action = fields.Char(string='الإجراء', required=True)
    owner = fields.Char(string='المسؤول')
    due_date = fields.Date(string='تاريخ التنفيذ')
    status = fields.Char(string='الحالة')
