# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpTimecard(models.Model):
    _name = 'simple.mrp.timecard'
    _description = "بطاقة وقت"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    worker_name = fields.Char(string="اسم العامل")
    badge_id = fields.Char(string="رقم البصمة")
    trade = fields.Char(string="المهنة")
    week_ending = fields.Date(string="نهاية الأسبوع")
    regular_hours = fields.Float(string="الساعات العادية")
    overtime_hours = fields.Float(string="الساعات الإضافية")
    leave_days = fields.Float(string="أيام الإجازة")
    week_total = fields.Float(string="إجمالي الأسبوع", compute='_compute_week_total')
    line_ids = fields.One2many(
        'simple.mrp.timecard.line', 'timecard_id', string="توزيع الساعات")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('regular_hours', 'overtime_hours')
    def _compute_week_total(self):
        for card in self:
            card.week_total = card.regular_hours + card.overtime_hours

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.timecard') or 'New'
        return super().create(vals_list)


class SimpleMrpTimecardLine(models.Model):
    _name = 'simple.mrp.timecard.line'
    _description = "بند بطاقة وقت"
    _order = 'id'

    timecard_id = fields.Many2one(
        'simple.mrp.timecard', string="البطاقة", required=True, ondelete='cascade')
    wo_ref = fields.Char(string="أمر التشغيل")
    task = fields.Char(string="المهمة")
    sat = fields.Float(string="السبت")
    sun = fields.Float(string="الأحد")
    mon = fields.Float(string="الإثنين")
    tue = fields.Float(string="الثلاثاء")
    wed = fields.Float(string="الأربعاء")
    thu = fields.Float(string="الخميس")
    total = fields.Float(string="الإجمالي", compute='_compute_total', store=True)

    @api.depends('sat', 'sun', 'mon', 'tue', 'wed', 'thu')
    def _compute_total(self):
        for line in self:
            line.total = (line.sat + line.sun + line.mon + line.tue
                          + line.wed + line.thu)
