# -*- coding: utf-8 -*-
"""Saudi Building Code (SBC) classification code.

A building/engineering classification (distinct from the procurement-oriented
rawasi.lcgpa.code). Used to tag reference items and price-intelligence records.
"""
from odoo import api, fields, models


class RawasiSbcCode(models.Model):
    _name = "rawasi.sbc.code"
    _description = "رمز كود البناء السعودي (SBC)"
    _order = "code"
    _rec_name = "display_label"

    code = fields.Char(string="الرمز", required=True, index=True)
    name = fields.Char(string="البند / الفصل", required=True, translate=True)
    display_label = fields.Char(compute="_compute_display_label", store=True)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز SBC يجب أن يكون فريداً.",
    )

    @api.depends("code", "name")
    def _compute_display_label(self):
        for rec in self:
            rec.display_label = "%s - %s" % (rec.code, rec.name) if rec.code else (rec.name or "")

    @api.model
    def match_code(self, raw_code):
        """Match a raw code string (e.g. '2002') against a record, or empty set."""
        if not raw_code:
            return self.browse()
        code = str(raw_code).strip()
        if not code or code == "غير محدد":
            return self.browse()
        return self.search([("code", "=", code)], limit=1)
