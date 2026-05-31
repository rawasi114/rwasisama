from odoo import models, fields, api, _
from .base import WORKSHOP_SCOPE


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_workshop_product = fields.Boolean(
        string='يُصنّع في الورشة',
        help='عند تفعيله يُنشأ أمر تصنيع تلقائياً عند تأكيد أمر بيع يحتوي هذا المنتج.')
    workshop_scope = fields.Selection(
        WORKSHOP_SCOPE, string='قسم التصنيع')
    workshop_material_ids = fields.One2many(
        'rwasi.product.material', 'product_tmpl_id', string='مواد التصنيع')


class ProductWorkshopMaterial(models.Model):
    _name = 'rwasi.product.material'
    _description = 'مادة خام لتصنيع المنتج'

    product_tmpl_id = fields.Many2one(
        'product.template', string='المنتج', required=True, ondelete='cascade')
    material_id = fields.Many2one(
        'product.product', string='المادة الخام', required=True,
        domain=[('purchase_ok', '=', True), ('sale_ok', '=', False)])
    qty = fields.Float(string='الكمية لكل وحدة', default=1.0)
    uom_name = fields.Char(
        related='material_id.uom_id.name', string='الوحدة')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    work_order_ids = fields.One2many(
        'rwasi.work.order', 'sale_order_id', string='أوامر التصنيع')
    work_order_count = fields.Integer(
        string='عدد أوامر التصنيع', compute='_compute_work_order_count')

    workshop_payment_ids = fields.One2many(
        'rwasi.customer.payment', 'sale_order_id', string='دفعات العميل')
    workshop_payment_count = fields.Integer(compute='_compute_workshop_payment')
    amount_paid = fields.Monetary(
        string='المُحصَّل', compute='_compute_workshop_payment',
        currency_field='currency_id')
    payment_ratio = fields.Float(
        string='نسبة السداد', compute='_compute_workshop_payment')

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for order in self:
            order.work_order_count = len(order.work_order_ids)

    @api.depends('workshop_payment_ids.amount', 'amount_total')
    def _compute_workshop_payment(self):
        for order in self:
            order.amount_paid = sum(order.workshop_payment_ids.mapped('amount'))
            order.workshop_payment_count = len(order.workshop_payment_ids)
            order.payment_ratio = (order.amount_paid / order.amount_total) \
                if order.amount_total else 0.0

    def action_view_workshop_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('دفعات العميل'),
            'res_model': 'rwasi.customer.payment',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._create_workshop_work_orders()
        return res

    def _create_workshop_work_orders(self):
        """ينشئ أمر تصنيع واحد لكل أمر بيع يحوي منتجات ورشية،
        مع أمر عمل لكل بند منتج ورشي + طلب مواد ابتدائي (مسودة) لكل أمر عمل."""
        self.ensure_one()
        if not self.company_id.workshop_auto_mo:
            return
        # تحقّق من وجود منتجات ورشية في الطلب
        workshop_lines = self.order_line.filtered(
            lambda l: l.product_id
            and l.product_id.product_tmpl_id.is_workshop_product
            and not l.display_type
        )
        if not workshop_lines:
            return
        # أمر تصنيع واحد فقط لكل أمر بيع
        wo = self.work_order_ids and self.work_order_ids[0]
        if not wo:
            wo = self.env['rwasi.work.order'].sudo().with_context(
                from_sale_order=True).create({
                    'sale_order_id': self.id,
                    'partner_id': self.partner_id.id,
                    'project_ref': self.name,
                })
        WorkJob = self.env['rwasi.work.job'].sudo()
        Request = self.env['rwasi.material.request'].sudo()
        for line in workshop_lines:
            # تفادي إنشاء أمر عمل مكرر لنفس البند
            if wo.job_ids.filtered(lambda j: j.sale_line_id.id == line.id):
                continue
            product = line.product_id
            tmpl = product.product_tmpl_id
            job = WorkJob.create({
                'work_order_id': wo.id,
                'sale_line_id': line.id,
                'product_id': product.id,
                'product_qty': line.product_uom_qty,
                'workshop_scope': tmpl.workshop_scope,
                'description': line.name,
            })
            # طلب مواد ابتدائي (مسودة) مُعبّأ من BOM المنتج
            material_vals = [
                (0, 0, {
                    'material_id': m.material_id.id,
                    'qty_needed': m.qty * line.product_uom_qty,
                })
                for m in tmpl.workshop_material_ids
            ]
            if material_vals:
                Request.create({
                    'work_order_id': wo.id,
                    'work_job_id': job.id,
                    'reason': 'initial',
                    'line_ids': material_vals,
                })

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('أوامر التصنيع'),
            'res_model': 'rwasi.work.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }
