# -*- coding: utf-8 -*-
"""ذاكرة الأسعار المؤسسية (Price Intelligence).

يُلتقط هنا كل بند مُسعَّر من جدول كميات منافسة مقدَّمة/فائزة/خاسرة، كي تُظهر
المنافسات المستقبلية «أسعاراً تاريخية مشابهة». المطابقة فجوية (SequenceMatcher
على نص عربي مطبَّع) — بلا pgvector أو إضافات قاعدة بيانات، فتبقى محمولة وقابلة للاختبار.
"""
from difflib import SequenceMatcher

from odoo import api, fields, models

from .arabic_utils import normalize_match


class RawasiPriceIntelligence(models.Model):
    _name = "rawasi.price.intelligence"
    _description = "ذاكرة الأسعار المؤسسية"
    _order = "price_date desc, id desc"

    name = fields.Text(string="وصف البند", required=True)
    name_normalized = fields.Char(string="الوصف المطبَّع", index=True)
    competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المصدر", ondelete="cascade", index=True
    )
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند جدول الكميات", ondelete="set null"
    )
    category = fields.Char(string="الفئة")
    uom_id = fields.Many2one("uom.uom", string="الوحدة")
    sbc_code_id = fields.Many2one("rawasi.sbc.code", string="رمز SBC")
    lcgpa_code_id = fields.Many2one("rawasi.lcgpa.code", string="رمز LCGPA")
    quantity = fields.Float(string="الكمية")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="العملة")
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    unit_price = fields.Monetary(string="سعر الوحدة")
    margin_pct = fields.Float(string="هامش %", compute="_compute_margin_pct", store=True)
    price_date = fields.Date(string="تاريخ التسعير", index=True)
    outcome = fields.Selection(
        [("submitted", "مقدَّمة"), ("won", "فائزة"), ("lost", "خاسرة")],
        string="نتيجة المنافسة",
        default="submitted",
        index=True,
    )

    @api.depends("unit_cost", "unit_price")
    def _compute_margin_pct(self):
        for rec in self:
            rec.margin_pct = (
                (rec.unit_price - rec.unit_cost) / rec.unit_cost * 100.0
                if rec.unit_cost
                else 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name_normalized"] = normalize_match(vals.get("name", ""))
        return super().create(vals_list)

    def write(self, vals):
        if "name" in vals:
            vals["name_normalized"] = normalize_match(vals.get("name", ""))
        return super().write(vals)

    @api.model
    def search_matches(
        self,
        text,
        uom_id=None,
        exclude_competition_id=None,
        limit=10,
        min_score=0.5,
        candidate_limit=2000,
    ):
        """مطابقة فجوية للأوصاف التاريخية. تُرجع قائمة (score, record) تنازلياً.

        التشابه يُحسب بـ SequenceMatcher.ratio() على النص المطبَّع، مع حافز بسيط
        عند تطابق الوحدة.
        """
        norm = normalize_match(text)
        if not norm:
            return []
        domain = []
        if exclude_competition_id:
            domain.append(("competition_id", "!=", exclude_competition_id))
        candidates = self.search(domain, limit=candidate_limit, order="price_date desc")
        matcher = SequenceMatcher()
        matcher.set_seq2(norm)
        scored = []
        for rec in candidates:
            matcher.set_seq1(rec.name_normalized or "")
            score = matcher.ratio()
            if uom_id and rec.uom_id.id == uom_id:
                score = min(1.0, score + 0.05)
            if score >= min_score:
                scored.append((score, rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:limit]
