# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpQualityCheck(models.Model):
    _name = 'simple.mrp.quality.check'
    _description = "فحص جودة"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    date = fields.Date(string="تاريخ الفحص", default=fields.Date.context_today)
    inspector_id = fields.Many2one(
        'res.users', string="المفتّش", default=lambda self: self.env.user)
    product_id = fields.Many2one('product.product', string="المنتج")
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    quantity = fields.Float(string="الكمية", default=1.0)
    line_ids = fields.One2many(
        'simple.mrp.quality.check.line', 'check_id', string="بنود الفحص")
    pass_rate = fields.Float(string="نسبة النجاح %", compute='_compute_pass_rate')

    state = fields.Selection([
        ('draft', "مسودة"),
        ('pass', "ناجح"),
        ('fail', "راسب"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids.result')
    def _compute_pass_rate(self):
        for check in self:
            scored = check.line_ids.filtered(lambda l: l.result in ('ok', 'nok'))
            if scored:
                ok = len(scored.filtered(lambda l: l.result == 'ok'))
                check.pass_rate = 100.0 * ok / len(scored)
            else:
                check.pass_rate = 0.0

    def action_pass(self):
        self.write({'state': 'pass'})
        return True

    def action_fail(self):
        self.write({'state': 'fail'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.quality.check') or 'New'
        return super().create(vals_list)


class SimpleMrpQualityCheckLine(models.Model):
    _name = 'simple.mrp.quality.check.line'
    _description = "بند فحص جودة"
    _order = 'id'

    check_id = fields.Many2one(
        'simple.mrp.quality.check', string="الفحص", required=True, ondelete='cascade')
    name = fields.Char(string="بند الفحص", required=True)
    result = fields.Selection([
        ('ok', "مطابق"),
        ('nok', "غير مطابق"),
        ('na', "غير منطبق"),
    ], string="النتيجة")
    note = fields.Char(string="ملاحظة")
