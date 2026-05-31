# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # يُعرَّف على القالب فقط؛ product.product يكتبه/يقرأه عبر تفويض _inherits.
    rawasi_reference_item_id = fields.Many2one(
        "rawasi.reference.item",
        string="البند المرجعي",
        help="البند المرجعي في كتالوج رواسي المرتبط بهذا المنتج.",
    )
    rawasi_procurement_type = fields.Selection(
        related="rawasi_reference_item_id.procurement_type",
        string="مسار توريد رواسي",
        store=True,
    )
