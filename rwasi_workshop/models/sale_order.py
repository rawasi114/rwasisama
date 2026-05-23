from odoo import models, fields, api, _
from .base import WORKSHOP_SCOPE


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_workshop_product = fields.Boolean(
        string='يُصنّع في الورشة',
        help='عند تفعيله يُنشأ أمر تصنيع تلقائياً عند تأكيد أمر بيع يحتوي هذا المنتج.')
    workshop_scope = fields.Selection(
        WORKSHOP_SCOPE, string='قسم التصنيع')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    work_order_ids = fields.One2many(
        'rwasi.work.order', 'sale_order_id', string='أوامر التصنيع')
    work_order_count = fields.Integer(
        string='عدد أوامر التصنيع', compute='_compute_work_order_count')

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for order in self:
            order.work_order_count = len(order.work_order_ids)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._create_workshop_work_orders()
        return res

    def _create_workshop_work_orders(self):
        """ينشئ أمر تصنيع لكل بند منتج يُصنّع في الورشة (تلقائياً وبصلاحية النظام)."""
        self.ensure_one()
        WorkOrder = self.env['rwasi.work.order'].sudo().with_context(from_sale_order=True)
        for line in self.order_line:
            product = line.product_id
            if not product or not product.product_tmpl_id.is_workshop_product:
                continue
            if line.display_type:
                continue
            existing = self.work_order_ids.filtered(
                lambda w: w.sale_line_id.id == line.id)
            if existing:
                continue
            WorkOrder.create({
                'sale_order_id': self.id,
                'sale_line_id': line.id,
                'partner_id': self.partner_id.id,
                'product_id': product.id,
                'product_qty': line.product_uom_qty,
                'scope_of_work': line.name,
                'workshop_scope': product.product_tmpl_id.workshop_scope,
                'project_ref': self.name,
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
