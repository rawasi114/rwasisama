# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import stock_ops


class SimpleMrpDelivery(models.Model):
    _name = 'simple.mrp.delivery'
    _description = "أمر تسليم"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string="العميل", tracking=True)
    delivery_address = fields.Char(string="عنوان التسليم")
    scheduled_date = fields.Date(
        string="التاريخ المجدول", default=fields.Date.context_today)
    date_done = fields.Datetime(string="تاريخ التسليم", readonly=True, copy=False)
    origin = fields.Char(string="المصدر", copy=False)
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    amount_total = fields.Float(string="الإجمالي", compute='_compute_amount_total')
    line_ids = fields.One2many(
        'simple.mrp.delivery.line', 'delivery_id', string="البنود")

    customer_signature = fields.Binary(string="توقيع العميل")
    customer_sign_name = fields.Char(string="اسم المستلم")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "تم التسليم"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for do in self:
            do.amount_total = sum(do.line_ids.mapped('amount'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for do in self:
            if do.partner_id:
                do.delivery_address = do.partner_id.contact_address

    def action_validate(self):
        for do in self:
            if do.state != 'draft':
                raise UserError(_("لا يمكن التحقق إلا من مسودة."))
            if not do.line_ids:
                raise UserError(_("لا توجد بنود للتسليم."))
            for line in do.line_ids:
                if stock_ops.available_qty(self.env, line.product_id) < line.qty:
                    raise UserError(
                        _("الكمية غير كافية بالمخزون للمنتج %s.")
                        % line.product_id.display_name)
            for line in do.line_ids:
                stock_ops.change_stock(self.env, line.product_id, -line.qty)
            do.state = 'done'
            do.date_done = fields.Datetime.now()
        return True

    def action_cancel(self):
        for do in self:
            if do.state == 'done':
                raise UserError(_("لا يمكن إلغاء تسليم تم تنفيذه."))
            do.state = 'cancel'
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.delivery') or 'New'
        return super().create(vals_list)


class SimpleMrpDeliveryLine(models.Model):
    _name = 'simple.mrp.delivery.line'
    _description = "بند تسليم"
    _order = 'id'

    delivery_id = fields.Many2one(
        'simple.mrp.delivery', string="التسليم", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="المنتج", required=True)
    qty = fields.Float(string="الكمية", default=1.0)
    available_qty = fields.Float(
        related='product_id.qty_available', string="المتاح")
    unit_price = fields.Float(string="سعر الوحدة")
    amount = fields.Float(string="الإجمالي", compute='_compute_amount')

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_price
