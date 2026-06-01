from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    material_request_id = fields.Many2one(
        'rwasi.material.request', string='طلب المواد',
        index=True, copy=False, ondelete='set null')
    workshop_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع',
        related='material_request_id.work_order_id',
        store=True, index=True)
