from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    workshop_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع', index=True, copy=False)
