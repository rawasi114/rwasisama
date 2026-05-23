# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpNcr(models.Model):
    _name = 'simple.mrp.ncr'
    _description = "تقرير عدم مطابقة"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    project = fields.Char(string="المشروع")
    item = fields.Char(string="العنصر")
    detected_on = fields.Date(string="تاريخ الرصد", default=fields.Date.context_today)
    description = fields.Text(string="الوصف")
    severity = fields.Selection([
        ('major', "كبرى"),
        ('minor', "صغرى"),
        ('observation', "ملاحظة"),
    ], string="الخطورة", default='minor')
    repeated = fields.Boolean(string="متكررة")
    root_cause = fields.Text(string="السبب الجذري")
    raised_by = fields.Char(string="رصدها")
    action_ids = fields.One2many(
        'simple.mrp.ncr.action', 'ncr_id', string="الإجراءات")

    state = fields.Selection([
        ('open', "مفتوحة"),
        ('closed', "مغلقة"),
        ('cancel', "ملغية"),
    ], string="الحالة", default='open', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    def action_close(self):
        self.write({'state': 'closed'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_reopen(self):
        self.write({'state': 'open'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.ncr') or 'New'
        return super().create(vals_list)


class SimpleMrpNcrAction(models.Model):
    _name = 'simple.mrp.ncr.action'
    _description = "إجراء تصحيحي"
    _order = 'id'

    ncr_id = fields.Many2one(
        'simple.mrp.ncr', string="عدم المطابقة", required=True, ondelete='cascade')
    name = fields.Char(string="الإجراء", required=True)
    owner = fields.Char(string="المسؤول")
    due_date = fields.Date(string="تاريخ التنفيذ")
    status = fields.Selection([
        ('open', "مفتوح"),
        ('done', "منجز"),
    ], string="الحالة", default='open')
