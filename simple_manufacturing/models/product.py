# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    bom_ids = fields.One2many(
        'simple.mrp.bom', 'product_id', string="قوائم المواد")
