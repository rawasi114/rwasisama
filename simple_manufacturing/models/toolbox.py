# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpToolbox(models.Model):
    _name = 'simple.mrp.toolbox'
    _description = "اجتماع سلامة"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    workshop = fields.Char(string="الورشة")
    topic = fields.Char(string="الموضوع")
    presenter = fields.Char(string="المُلقي")
    key_points = fields.Text(string="النقاط الرئيسية")
    hz_cuts = fields.Boolean(string="القطع والجروح")
    hz_fall = fields.Boolean(string="السقوط")
    hz_electrical = fields.Boolean(string="الكهرباء")
    hz_fire = fields.Boolean(string="الحريق")
    hz_lifting = fields.Boolean(string="الأحمال الثقيلة")
    hz_heat = fields.Boolean(string="الحرارة")
    hz_chemicals = fields.Boolean(string="الكيماويات")
    hz_noise = fields.Boolean(string="الضوضاء")
    line_ids = fields.One2many(
        'simple.mrp.toolbox.attendee', 'toolbox_id', string="الحضور")

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.toolbox') or 'New'
        return super().create(vals_list)


class SimpleMrpToolboxAttendee(models.Model):
    _name = 'simple.mrp.toolbox.attendee'
    _description = "حاضر اجتماع سلامة"
    _order = 'id'

    toolbox_id = fields.Many2one(
        'simple.mrp.toolbox', string="الاجتماع", required=True, ondelete='cascade')
    worker_name = fields.Char(string="الاسم", required=True)
    badge_id = fields.Char(string="رقم البصمة")
    trade = fields.Char(string="المهنة")
