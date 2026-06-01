# -*- coding: utf-8 -*-
"""ترحيل بعد الترقية إلى الإصدار 19.0.9.0.0.

نضمن أن كل وحدة (rawasi.unit) موجودة من قبل لها مقابل في uom.uom.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    units = env["rawasi.unit"].search([("uom_id", "=", False)])
    if units:
        units._ensure_uom()
