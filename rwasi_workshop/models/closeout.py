from odoo import models, fields


# ============================================================
# RS-WS-20 — إغلاق وتسليم المشروع (Project Closeout & Handover)
# ============================================================
class ProjectCloseout(models.Model):
    _name = 'rwasi.project.closeout'
    _description = 'إغلاق وتسليم المشروع (RS-WS-20)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.project.closeout'

    contract_no = fields.Char(string='رقم العقد')
    handover_date = fields.Date(string='تاريخ التسليم')

    checklist_ids = fields.One2many(
        'rwasi.closeout.line', 'closeout_id', string='قائمة التحقق من الإغلاق')
    punch_ids = fields.One2many(
        'rwasi.punch.line', 'closeout_id', string='قائمة الملاحظات المتبقية')

    handover_statement = fields.Text(string='إقرار التسليم النهائي')

    # مدير المشروع / ممثل العميل
    pm_name = fields.Char(string='مدير المشروع - الاسم')
    pm_date = fields.Date(string='مدير المشروع - التاريخ')
    pm_signature = fields.Binary(string='مدير المشروع - التوقيع')
    client_rep_name = fields.Char(string='ممثل العميل - الاسم')
    client_rep_date = fields.Date(string='ممثل العميل - التاريخ')
    client_rep_signature = fields.Binary(string='ممثل العميل - التوقيع')
    client_stamp = fields.Binary(string='ختم العميل')


class CloseoutLine(models.Model):
    _name = 'rwasi.closeout.line'
    _description = 'بند تحقق من الإغلاق'
    _order = 'sequence, id'

    closeout_id = fields.Many2one(
        'rwasi.project.closeout', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    item = fields.Char(string='البند', required=True)
    result = fields.Selection([
        ('yes', 'يطابق'),
        ('no', 'لا يطابق'),
        ('na', 'غير منطبق'),
    ], string='النتيجة')
    reference = fields.Char(string='المرجع')


class PunchLine(models.Model):
    _name = 'rwasi.punch.line'
    _description = 'بند ملاحظة متبقية (Punch List)'
    _order = 'sequence, id'

    closeout_id = fields.Many2one(
        'rwasi.project.closeout', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    description = fields.Char(string='الوصف', required=True)
    owner = fields.Char(string='المسؤول')
    close_date = fields.Date(string='تاريخ الإغلاق')
