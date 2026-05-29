# -*- coding: utf-8 -*-
from difflib import SequenceMatcher

from odoo import api, fields, models

from .arabic_utils import normalize_match


class RawasiPriceIntelligence(models.Model):
    _name = "rawasi.price.intelligence"
    _description = "ذاكرة الأسعار المؤسسية (Price Intelligence)"
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
    unit_id = fields.Many2one("rawasi.unit", string="الوحدة")
    unit_text = fields.Char(string="الوحدة (نص)")
    sbc_code_id = fields.Many2one("rawasi.sbc.code", string="رمز SBC")
    lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        help="رمز هيئة المحتوى المحلي والمشتريات الحكومية.",
    )
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي",
        index=True,
        help="ربط بكتالوج البنود المرجعية الموحَّد.",
    )
    reference_match_source = fields.Selection(
        [
            ("exact_text",  "تطابق نصي كامل"),
            ("lcgpa_code",  "تطابق برمز LCGPA"),
            ("spec_pattern","تطابق بنمط المواصفات"),
            ("pgvector",    "تطابق دلالي"),
            ("manual",      "ربط يدوي"),
        ],
        string="مصدر الربط بالكتالوج",
    )
    reference_match_confidence = fields.Float(string="ثقة الربط %")
    quantity = fields.Float(string="الكمية")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="العملة")
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    unit_price = fields.Monetary(string="سعر الوحدة")
    margin_pct = fields.Float(string="هامش %")
    price_date = fields.Date(string="تاريخ التسعير", index=True)
    outcome = fields.Selection(
        [("submitted", "مقدَّم"), ("won", "فائز"), ("lost", "خاسر")],
        string="نتيجة المنافسة",
        default="submitted",
        index=True,
    )

    @api.model
    def search_matches(
        self,
        text,
        unit_id=None,
        exclude_competition_id=None,
        limit=10,
        min_score=0.5,
        candidate_limit=2000,
    ):
        """مطابقة فجوية للأوصاف التاريخية. تُرجع قائمة (score, record) تنازلياً.

        التشابه يُحسب بـ SequenceMatcher على النص المطبَّع، مع حافز بسيط
        لتطابق الوحدة. لا تعتمد على إضافات قاعدة البيانات (pg_trgm) كي تبقى
        محمولة وقابلة للاختبار.
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
            if unit_id and rec.unit_id.id == unit_id:
                score = min(1.0, score + 0.05)
            if score >= min_score:
                scored.append((score, rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:limit]
