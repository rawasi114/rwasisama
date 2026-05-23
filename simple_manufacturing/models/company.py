# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    workshop_auto_mo = fields.Boolean(
        string="توليد أوامر التصنيع تلقائياً من المبيعات",
        default=False,
        help="عند تفعيله يُنشأ أمر تصنيع تلقائياً عند تأكيد أمر بيع في هذه الشركة.")
