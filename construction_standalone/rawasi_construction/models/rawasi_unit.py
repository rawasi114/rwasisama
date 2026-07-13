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
    uom_id = fields.Many2one(
        "uom.uom",
        string="وحدة Odoo القياسية",
        ondelete="restrict",
        help="ربط وحدة كراسة الشروط بوحدة قياس Odoo القياسية. يُنشأ تلقائياً عند الحفظ إن لم يُحدَّد.",
    )
    active = fields.Boolean(default=True)

    # خريطة الأنواع → وحدة مرجعية في Odoo (للوحدات الجديدة المُنشأة تلقائياً).
    _REFERENCE_UOM_XMLID = {
        "length": "uom.product_uom_meter",
        "area": "uom.product_uom_square_meter",
        "volume": "uom.product_uom_cubic_meter",
        "count": "uom.product_uom_unit",
        "mass": "uom.product_uom_kgm",
        "system": "uom.product_uom_unit",
    }

    def _ensure_uom(self):
        """Auto-create or link a uom.uom record for this construction unit."""
        Uom = self.env["uom.uom"]
        for unit in self:
            if unit.uom_id:
                continue
            existing = Uom.search([("name", "=", unit.name)], limit=1)
            if existing:
                unit.uom_id = existing.id
                continue
            ref_xmlid = self._REFERENCE_UOM_XMLID.get(unit.uom_category, "uom.product_uom_unit")
            reference = self.env.ref(ref_xmlid, raise_if_not_found=False) or \
                        self.env.ref("uom.product_uom_unit")
            unit.uom_id = Uom.create({
                "name": unit.name,
                "relative_factor": 1.0,
                "relative_uom_id": reference.id,
            }).id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_uom()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "name" in vals or "uom_category" in vals:
            self._ensure_uom()
        return res

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
