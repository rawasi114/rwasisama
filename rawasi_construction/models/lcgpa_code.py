# -*- coding: utf-8 -*-
"""LCGPA classification code — Local Content & Government Procurement Authority.

Appears in the "construction code" column of Etimad BoQ files and points to a
standardized classification of the item among mandatory local products. Distinct
from the Saudi Building Code (rawasi.sbc.code): this is a procurement
classification, the other is a building classification.
"""
from odoo import api, fields, models


class RawasiLcgpaCode(models.Model):
    _name = "rawasi.lcgpa.code"
    _description = "رمز LCGPA — هيئة المحتوى المحلي"
    _order = "code"
    _rec_name = "display_label"

    code = fields.Char(string="الرمز", required=True, index=True, size=10)
    name_ar = fields.Char(string="الاسم العربي", required=True)
    name_en = fields.Char(string="Name (English)")
    category = fields.Char(string="التصنيف العام", index=True)
    description = fields.Text(string="الوصف")
    is_mandatory_local = fields.Boolean(string="منتج إلزامي محلي", default=True)
    display_label = fields.Char(compute="_compute_display_label", store=True)
    reference_item_ids = fields.One2many(
        "rawasi.reference.item", "lcgpa_code_id", string="البنود المرجعية المرتبطة"
    )
    reference_item_count = fields.Integer(compute="_compute_reference_item_count")
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز LCGPA يجب أن يكون فريداً.",
    )

    @api.depends("code", "name_ar")
    def _compute_display_label(self):
        for rec in self:
            rec.display_label = "[%s] %s" % (rec.code or "", rec.name_ar or "")

    @api.depends("reference_item_ids")
    def _compute_reference_item_count(self):
        for rec in self:
            rec.reference_item_count = len(rec.reference_item_ids)

    @api.model
    def match_code(self, raw_code):
        """Match a raw code string against a record, or return an empty recordset."""
        if not raw_code:
            return self.browse()
        code = str(raw_code).strip()
        if not code or code == "غير محدد":
            return self.browse()
        return self.search([("code", "=", code)], limit=1)
