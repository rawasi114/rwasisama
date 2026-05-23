# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import stock_ops


class SimpleMrpPurchaseRequest(models.Model):
    _name = 'simple.mrp.purchase.request'
    _description = "طلب شراء التصنيع"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    vendor_id = fields.Many2one('res.partner', string="المورّد", tracking=True)
    date_order = fields.Date(
        string="تاريخ الطلب", default=fields.Date.context_today, tracking=True)
    date_received = fields.Date(string="تاريخ الاستلام", readonly=True, copy=False)
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    origin = fields.Char(string="المصدر", copy=False)
    po_number = fields.Char(string="رقم أمر الشراء")
    invoice_number = fields.Char(string="رقم الفاتورة")
    amount_total = fields.Float(string="الإجمالي", compute='_compute_amount_total')
    line_ids = fields.One2many(
        'simple.mrp.purchase.request.line', 'request_id', string="البنود")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('confirmed', "مؤكد"),
        ('partial', "استلام جزئي"),
        ('received', "مستلم"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for req in self:
            req.amount_total = sum(req.line_ids.mapped('amount'))

    def action_confirm(self):
        for req in self:
            if req.state == 'draft':
                req.state = 'confirmed'
        return True

    def action_receive(self):
        for req in self:
            if req.state not in ('confirmed', 'partial'):
                raise UserError(_("يجب تأكيد الطلب قبل الاستلام."))
            posted = False
            for line in req.line_ids:
                if line.received_qty and line.received_qty > 0:
                    stock_ops.change_stock(self.env, line.product_id, line.received_qty)
                    line.qty_received += line.received_qty
                    line.received_qty = 0.0
                    posted = True
            if not posted:
                raise UserError(
                    _("أدخل الكمية المستلمة في حقل \"الكمية المستلمة الآن\" لبند واحد على الأقل."))
            req.date_received = fields.Date.context_today(req)
            if all(l.qty_received >= l.qty for l in req.line_ids):
                req.state = 'received'
            else:
                req.state = 'partial'
        return True

    def action_cancel(self):
        for req in self:
            if req.state in ('received', 'partial'):
                raise UserError(
                    _("لا يمكن إلغاء طلب تم استلامه كلياً أو جزئياً."))
            req.state = 'cancel'
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.purchase.request') or 'New'
        return super().create(vals_list)


class SimpleMrpPurchaseRequestLine(models.Model):
    _name = 'simple.mrp.purchase.request.line'
    _description = "بند طلب شراء"
    _order = 'id'

    request_id = fields.Many2one(
        'simple.mrp.purchase.request', string="الطلب", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="المنتج", required=True)
    qty = fields.Float(string="الكمية المطلوبة", default=1.0)
    unit_cost = fields.Float(string="سعر الوحدة")
    amount = fields.Float(string="الإجمالي", compute='_compute_amount')
    received_qty = fields.Float(string="الكمية المستلمة الآن")
    qty_received = fields.Float(string="إجمالي المستلم", readonly=True)
    conformance = fields.Selection([
        ('conforming', "مطابق"),
        ('conditional', "قبول مشروط"),
        ('rejected', "مرفوض"),
    ], string="المطابقة")

    @api.depends('qty', 'unit_cost')
    def _compute_amount(self):
        for line in self:
            line.amount = line.qty * line.unit_cost
