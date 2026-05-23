# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import stock_ops


class SimpleMrpBom(models.Model):
    _name = 'simple.mrp.bom'
    _description = "قائمة المواد"
    _inherit = ['mail.thread']
    _order = 'id desc'

    code = fields.Char(string="الرمز", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    product_id = fields.Many2one(
        'product.product', string="المنتج", required=True, tracking=True)
    product_qty = fields.Float(string="الكمية المنتجة", default=1.0, tracking=True)
    uom_name = fields.Char(related='product_id.uom_id.name', string="الوحدة")
    line_ids = fields.One2many(
        'simple.mrp.bom.line', 'bom_id', string="المكوّنات")
    component_count = fields.Integer(
        string="عدد المكوّنات", compute='_compute_component_count')
    active = fields.Boolean(default=True)
    notes = fields.Text(string="ملاحظات")
    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids')
    def _compute_component_count(self):
        for bom in self:
            bom.component_count = len(bom.line_ids)

    @api.depends('code', 'product_id')
    def _compute_display_name(self):
        for bom in self:
            if bom.product_id:
                bom.display_name = "%s - %s" % (bom.code or _('جديد'),
                                                bom.product_id.display_name)
            else:
                bom.display_name = bom.code or _('جديد')

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for bom in self:
            if bom.product_qty <= 0:
                raise ValidationError(_("الكمية المنتجة يجب أن تكون أكبر من صفر."))

    @api.constrains('product_id', 'line_ids')
    def _check_no_self_component(self):
        for bom in self:
            if bom.product_id and bom.product_id in bom.line_ids.mapped('component_id'):
                raise ValidationError(
                    _("لا يمكن أن يكون المنتج مكوّناً لنفسه في قائمة المواد."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') in (False, 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.bom') or 'New'
        return super().create(vals_list)


class SimpleMrpBomLine(models.Model):
    _name = 'simple.mrp.bom.line'
    _description = "مكوّن قائمة المواد"
    _order = 'sequence, id'

    sequence = fields.Integer(string="م.", default=10)
    bom_id = fields.Many2one(
        'simple.mrp.bom', string="قائمة المواد", required=True, ondelete='cascade')
    component_id = fields.Many2one(
        'product.product', string="المكوّن", required=True)
    qty = fields.Float(string="الكمية", default=1.0)
    uom_name = fields.Char(related='component_id.uom_id.name', string="الوحدة")
    available_qty = fields.Float(
        string="المتاح بالمخزون", compute='_compute_available_qty')

    @api.depends('component_id')
    def _compute_available_qty(self):
        for line in self:
            line.available_qty = stock_ops.available_qty(self.env, line.component_id)

    @api.constrains('qty')
    def _check_qty(self):
        for line in self:
            if line.qty <= 0:
                raise ValidationError(_("كمية المكوّن يجب أن تكون أكبر من صفر."))
