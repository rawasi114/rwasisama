# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpSurvey(models.Model):
    _name = 'simple.mrp.survey'
    _description = "معاينة موقع"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string="العميل", tracking=True)
    phone = fields.Char(related='partner_id.phone', string="الهاتف")
    site_address = fields.Char(string="عنوان الموقع")
    project = fields.Char(string="المشروع")
    date = fields.Date(string="تاريخ المعاينة", default=fields.Date.context_today)
    surveyor_id = fields.Many2one(
        'res.users', string="القائم بالمعاينة", default=lambda self: self.env.user)
    line_ids = fields.One2many(
        'simple.mrp.survey.line', 'survey_id', string="القياسات")
    total_area = fields.Float(string="إجمالي المساحة", compute='_compute_total_area')

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجزة"),
        ('cancel', "ملغية"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids.area')
    def _compute_total_area(self):
        for survey in self:
            survey.total_area = sum(survey.line_ids.mapped('area'))

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.survey') or 'New'
        return super().create(vals_list)


class SimpleMrpSurveyLine(models.Model):
    _name = 'simple.mrp.survey.line'
    _description = "بند معاينة"
    _order = 'id'

    survey_id = fields.Many2one(
        'simple.mrp.survey', string="المعاينة", required=True, ondelete='cascade')
    location = fields.Char(string="الموقع")
    description = fields.Char(string="الوصف")
    width = fields.Float(string="العرض")
    height = fields.Float(string="الارتفاع")
    depth = fields.Float(string="العمق")
    quantity = fields.Float(string="العدد", default=1.0)
    area = fields.Float(string="المساحة", compute='_compute_area', store=True)
    note = fields.Char(string="ملاحظة")

    @api.depends('width', 'height', 'quantity')
    def _compute_area(self):
        for line in self:
            line.area = line.width * line.height * (line.quantity or 1.0)
