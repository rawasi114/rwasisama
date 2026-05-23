# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpDailyPrep(models.Model):
    _name = 'simple.mrp.daily.prep'
    _description = "التحضير اليومي"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    workshop = fields.Char(string="الورشة")
    shift_supervisor = fields.Char(string="مشرف الوردية")
    line_ids = fields.One2many(
        'simple.mrp.daily.prep.line', 'prep_id', string="الأعمال المخططة")
    available_crew = fields.Integer(string="الطاقم المتاح")
    absent_crew = fields.Integer(string="الغائبون")
    ready_equipment = fields.Integer(string="معدات جاهزة")
    maintenance_equipment = fields.Integer(string="تحت الصيانة")
    materials_ready = fields.Boolean(string="مواد متوفرة")
    drawings_approved = fields.Boolean(string="مخططات معتمدة")
    toolbox_done = fields.Boolean(string="اجتماع سلامة")
    ppe_verified = fields.Boolean(string="أدوات الحماية")
    targets_reviewed = fields.Boolean(string="مراجعة الأهداف")
    bottlenecks = fields.Text(string="المعوقات المتوقعة")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

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
                    'simple.mrp.daily.prep') or 'New'
        return super().create(vals_list)


class SimpleMrpDailyPrepLine(models.Model):
    _name = 'simple.mrp.daily.prep.line'
    _description = "بند تحضير يومي"
    _order = 'id'

    prep_id = fields.Many2one(
        'simple.mrp.daily.prep', string="التحضير", required=True, ondelete='cascade')
    wo_ref = fields.Char(string="أمر التشغيل")
    task = fields.Char(string="المهمة", required=True)
    assigned_to = fields.Char(string="المسؤول")
    hours = fields.Float(string="الساعات")
    expected_output = fields.Char(string="المخرج المتوقع")


class SimpleMrpDailyReport(models.Model):
    _name = 'simple.mrp.daily.report'
    _description = "التقرير اليومي"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    workshop = fields.Char(string="الورشة")
    weather = fields.Char(string="الطقس")
    working_hours = fields.Char(string="ساعات العمل")
    crew_count = fields.Integer(string="عدد الطاقم")
    man_hours = fields.Float(string="إجمالي ساعات العمل")
    equipment_used = fields.Char(string="المعدات المستخدمة")
    line_ids = fields.One2many(
        'simple.mrp.daily.report.line', 'report_id', string="الإنجازات")
    issues = fields.Text(string="المعوقات")
    plan_tomorrow = fields.Text(string="خطة الغد")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

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
                    'simple.mrp.daily.report') or 'New'
        return super().create(vals_list)


class SimpleMrpDailyReportLine(models.Model):
    _name = 'simple.mrp.daily.report.line'
    _description = "بند تقرير يومي"
    _order = 'id'

    report_id = fields.Many2one(
        'simple.mrp.daily.report', string="التقرير", required=True, ondelete='cascade')
    wo_ref = fields.Char(string="أمر التشغيل")
    description = fields.Char(string="الوصف", required=True)
    planned = fields.Float(string="المخطط")
    done = fields.Float(string="المنجز")
    completion = fields.Float(string="% الإنجاز", compute='_compute_completion', store=True)
    remaining = fields.Float(string="المتبقي", compute='_compute_completion', store=True)

    @api.depends('planned', 'done')
    def _compute_completion(self):
        for line in self:
            line.completion = (100.0 * line.done / line.planned) if line.planned else 0.0
            line.remaining = line.planned - line.done
