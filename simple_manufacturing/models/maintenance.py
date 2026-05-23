# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpMaintenance(models.Model):
    _name = 'simple.mrp.maintenance'
    _description = "سجل صيانة"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    machine = fields.Char(string="المعدة", required=True)
    asset_no = fields.Char(string="رقم الأصل")
    location = fields.Char(string="الموقع")
    year = fields.Char(string="سنة الإنتاج")
    frequency = fields.Selection([
        ('daily', "يومي"),
        ('weekly', "أسبوعي"),
        ('monthly', "شهري"),
        ('quarterly', "ربع سنوي"),
        ('annual', "سنوي"),
    ], string="دورية الصيانة", default='monthly')
    line_ids = fields.One2many(
        'simple.mrp.maintenance.line', 'maintenance_id', string="أعمال الصيانة")

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.maintenance') or 'New'
        return super().create(vals_list)


class SimpleMrpMaintenanceLine(models.Model):
    _name = 'simple.mrp.maintenance.line'
    _description = "بند صيانة"
    _order = 'id'

    maintenance_id = fields.Many2one(
        'simple.mrp.maintenance', string="السجل", required=True, ondelete='cascade')
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    work_type = fields.Selection([
        ('preventive', "وقائية"),
        ('corrective', "علاجية"),
    ], string="النوع", default='preventive')
    work = fields.Char(string="العمل/العطل", required=True)
    spares = fields.Char(string="قطع الغيار")
    downtime = fields.Float(string="ساعات التوقف")
    technician = fields.Char(string="الفني")
