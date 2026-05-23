# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import stock_ops


class SimpleMrpMaterialRequest(models.Model):
    _name = 'simple.mrp.material.request'
    _description = "طلب مواد"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    requester_id = fields.Many2one(
        'res.users', string="مقدّم الطلب", default=lambda self: self.env.user)
    department = fields.Char(string="القسم")
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    reason = fields.Text(string="سبب الطلب")
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    project = fields.Char(string="المشروع")
    cost_center = fields.Char(string="مركز التكلفة")
    job_no = fields.Char(string="رقم العمل")
    boq_item = fields.Char(string="رقم البند")
    receiver_id = fields.Many2one('res.users', string="المستلم")
    date_issued = fields.Date(string="تاريخ الصرف", readonly=True, copy=False)
    line_ids = fields.One2many(
        'simple.mrp.material.request.line', 'request_id', string="البنود")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('approved', "معتمد"),
        ('issued', "تم الصرف"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    def action_approve(self):
        for req in self:
            if req.state == 'draft':
                req.state = 'approved'
        return True

    def action_issue(self):
        for req in self:
            if req.state != 'approved':
                raise UserError(_("يجب اعتماد الطلب قبل الصرف."))
            for line in req.line_ids:
                if line.net_qty and line.net_qty > 0:
                    if stock_ops.available_qty(self.env, line.product_id) < line.net_qty:
                        raise UserError(
                            _("الكمية غير كافية بالمخزون للمنتج %s.")
                            % line.product_id.display_name)
            for line in req.line_ids:
                if line.net_qty and line.net_qty > 0:
                    stock_ops.change_stock(self.env, line.product_id, -line.net_qty)
            req.state = 'issued'
            req.date_issued = fields.Date.context_today(req)
        return True

    def action_cancel(self):
        for req in self:
            if req.state == 'issued':
                raise UserError(_("لا يمكن إلغاء طلب تم صرفه."))
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
                    'simple.mrp.material.request') or 'New'
        return super().create(vals_list)


class SimpleMrpMaterialRequestLine(models.Model):
    _name = 'simple.mrp.material.request.line'
    _description = "بند طلب مواد"
    _order = 'id'

    request_id = fields.Many2one(
        'simple.mrp.material.request', string="الطلب", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="المنتج", required=True)
    qty = fields.Float(string="الكمية", default=1.0)
    available_qty = fields.Float(
        related='product_id.qty_available', string="المتاح")
    purpose = fields.Char(string="الغرض")
    returned_qty = fields.Float(string="المرتجع")
    net_qty = fields.Float(string="الصافي", compute='_compute_net_qty', store=True)
    bin_card = fields.Char(string="رقم البطاقة")

    @api.depends('qty', 'returned_qty')
    def _compute_net_qty(self):
        for line in self:
            line.net_qty = line.qty - line.returned_qty
