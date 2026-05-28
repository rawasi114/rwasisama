# -*- coding: utf-8 -*-
"""أكواد LCGPA — هيئة المحتوى المحلي والمشتريات الحكومية.

تظهر هذه الأكواد في عمود «الرمز الإنشائي» من ملفات اعتماد، وتشير إلى
تصنيف موحَّد للبند ضمن قائمة المنتجات الإلزامية المحلية.

أمثلة:
- 2002: الخرسانة
- 2031: الأبواب الخشبية
- 2041: الأنابيب
"""
from odoo import fields, models


class LCGPACode(models.Model):
    _name = "rawasi.lcgpa.code"
    _description = "رمز LCGPA (المحتوى المحلي)"
    _order = "code"
    _rec_name = "display_label"

    code = fields.Char(string="الرمز", required=True, index=True, size=10)
    name_ar = fields.Char(string="الاسم العربي", required=True)
    name_en = fields.Char(string="Name (English)")
    description = fields.Text(string="الوصف")
    category = fields.Char(string="التصنيف العام", index=True)
    is_mandatory_local = fields.Boolean(
        string="منتج إلزامي محلي", default=True,
        help="هل البند ضمن قائمة المنتجات الإلزامية للمحتوى المحلي.",
    )
    display_label = fields.Char(
        string="العرض", compute="_compute_display_label", store=True,
    )
    reference_item_ids = fields.One2many(
        "rawasi.reference.item", "lcgpa_code_id",
        string="البنود المرجعية المرتبطة",
    )
    reference_item_count = fields.Integer(
        string="عدد البنود", compute="_compute_reference_item_count",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز LCGPA يجب أن يكون فريداً.",
    )

    def _compute_display_label(self):
        for rec in self:
            rec.display_label = "[%s] %s" % (rec.code or "", rec.name_ar or "")

    def _compute_reference_item_count(self):
        for rec in self:
            rec.reference_item_count = len(rec.reference_item_ids)
