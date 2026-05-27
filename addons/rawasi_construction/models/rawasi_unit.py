# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from .arabic_utils import normalize_unit


class RawasiUnit(models.Model):
    _name = "rawasi.unit"
    _description = "وحدة قياس (مع مرادفات للتطبيع)"
    _order = "name"

    name = fields.Char(string="الوحدة", required=True, translate=True)
    code = fields.Char(string="الرمز القياسي", required=True)
    uom_category = fields.Selection(
        [
            ("length", "طول"),
            ("area", "مساحة"),
            ("volume", "حجم"),
            ("count", "عدد"),
            ("mass", "كتلة"),
            ("system", "نظام/مقطوعية"),
        ],
        string="التصنيف",
        default="count",
    )
    alias_raw = fields.Text(
        string="المرادفات",
        help="قائمة بأشكال كتابة الوحدة (سطر أو فاصلة لكل شكل). تُطبَّع تلقائياً للمطابقة.",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "الرمز القياسي للوحدة يجب أن يكون فريداً.",
    )

    def _normalized_aliases(self):
        """مجموعة المرادفات المطبَّعة لهذه الوحدة (شاملةً الاسم والرمز)."""
        self.ensure_one()
        raw = self.alias_raw or ""
        tokens = re.split(r"[\n,]+", raw) if raw else []
        tokens += [self.name or "", self.code or ""]
        return {normalize_unit(t) for t in tokens if t and normalize_unit(t)}

    @api.model
    def build_alias_index(self):
        """يبني خريطة {مرادف مطبَّع -> سجل وحدة} لكل الوحدات النشطة."""
        index = {}
        for unit in self.search([]):
            for alias in unit._normalized_aliases():
                index.setdefault(alias, unit)
        return index

    @api.model
    def match(self, raw_text):
        """يطابق نص وحدة خام مع سجل وحدة، أو يعيد سجلاً فارغاً."""
        token = normalize_unit(raw_text)
        if not token:
            return self.browse()
        return self.build_alias_index().get(token, self.browse())
