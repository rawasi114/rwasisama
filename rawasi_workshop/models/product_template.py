# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    rawasi_produce_in_workshop = fields.Boolean(
        string="يُصنَّع في الورشة",
        help="عند تأكيد أمر بيع يحتوي هذا المنتج، يُنشأ أمر تصنيع ورشة تلقائياً.",
    )
    rawasi_workshop_section_id = fields.Many2one(
        "rawasi.workshop.section", string="قسم التصنيع"
    )
