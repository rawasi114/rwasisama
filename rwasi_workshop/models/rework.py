from odoo import models, fields, api


# ============================================================
# RS-WS-23 — إعادة أعمال (Rework Order)
# ============================================================
class Rework(models.Model):
    _name = 'rwasi.rework'
    _description = 'إعادة أعمال (RS-WS-23)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.rework'

    work_order_id = fields.Many2one('rwasi.work.order', string='أمر التصنيع')
    ncr_id = fields.Many2one('rwasi.ncr', string='تقرير عدم المطابقة المرتبط')
    item = fields.Char(string='العنصر / البند')
    reason = fields.Selection([
        ('defect', 'عيب تصنيع'),
        ('damage', 'تلف'),
        ('spec_change', 'تغيير مواصفة'),
        ('material', 'مشكلة مواد'),
        ('other', 'أخرى'),
    ], string='سبب إعادة العمل', default='defect')
    description = fields.Text(string='وصف إعادة العمل')
    qty = fields.Float(string='الكمية', default=1.0)
    responsible = fields.Char(string='المسؤول عن التنفيذ')
    rework_date = fields.Date(
        string='تاريخ إعادة العمل', default=fields.Date.context_today)
    est_hours = fields.Float(string='الساعات التقديرية')
    cost = fields.Float(string='التكلفة التقديرية')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد التنفيذ'),
        ('done', 'منجز'),
        ('cancel', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True, group_expand='_expand_states')

    @api.model
    def _expand_states(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

    def action_start(self):
        self.write({'state': 'in_progress'})
        return True

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True
