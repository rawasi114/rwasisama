# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # توقيعات رقمية معتمدة تُستخدم في التقارير (المقاولات + الورشة)
    rawasi_signature_site_engineer = fields.Binary(string="توقيع مهندس الموقع")
    rawasi_signature_project_manager = fields.Binary(string="توقيع مدير المشروع")
    rawasi_signature_technical = fields.Binary(string="توقيع المكتب الفني")
    rawasi_signature_accountant = fields.Binary(string="توقيع المحاسب")
