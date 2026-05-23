# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpAttendance(models.Model):
    _name = 'simple.mrp.attendance'
    _description = "حضور العمالة"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    workshop = fields.Char(string="الورشة")
    shift = fields.Selection([
        ('day', "نهارية"),
        ('night', "ليلية"),
    ], string="الوردية", default='day')
    line_ids = fields.One2many(
        'simple.mrp.attendance.line', 'attendance_id', string="الحضور")
    total_present = fields.Integer(string="إجمالي الحضور", compute='_compute_total_present')

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids')
    def _compute_total_present(self):
        for sheet in self:
            sheet.total_present = len(sheet.line_ids)

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
                    'simple.mrp.attendance') or 'New'
        return super().create(vals_list)


class SimpleMrpAttendanceLine(models.Model):
    _name = 'simple.mrp.attendance.line'
    _description = "بند حضور"
    _order = 'id'

    attendance_id = fields.Many2one(
        'simple.mrp.attendance', string="الكشف", required=True, ondelete='cascade')
    badge_id = fields.Char(string="رقم البصمة")
    worker_name = fields.Char(string="اسم العامل", required=True)
    trade = fields.Char(string="المهنة")
    time_in = fields.Char(string="الدخول")
    time_out = fields.Char(string="الخروج")
    overtime = fields.Float(string="إضافي")
    total_hours = fields.Float(string="إجمالي الساعات")
