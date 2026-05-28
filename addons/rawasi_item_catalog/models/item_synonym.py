# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


# Tashkeel (Arabic diacritics): fatha, kasra, damma, sukun, shadda, tanween,
# plus dagger alef and Quranic annotation marks.
_ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"

# Alef variants (آ أ إ) collapse to plain alef (ا).
_ALEF_VARIANTS = re.compile(r"[آأإ]")
# Alef maksura (ى) and ya (ي) are conflated in most matching scenarios.
_ALEF_MAKSURA = "ى"  # → ي
# Ta marbuta (ة) stays distinct on purpose — many domain terms rely on it
# (e.g. ساعة vs ساعه change meaning subtly in technical specs).

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_EAST_AR_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_WHITESPACE = re.compile(r"\s+")


def normalize_arabic(text):
    """طبِّع النص العربي للمطابقة الدلالية والفهرسة.

    خطوات: إزالة التشكيل، التطويل، توحيد الألف/الياء، تحويل الأرقام
    العربية والفارسية إلى لاتينية، طي المسافات، تحويل اللاتيني إلى صغير.
    تُبقي ة (تاء مربوطة) كما هي لتفادي خلط دلالي في المصطلحات الفنية.
    """
    if not text:
        return ""
    s = text.strip()
    s = _ARABIC_DIACRITICS.sub("", s)
    s = s.replace(_TATWEEL, "")
    s = _ALEF_VARIANTS.sub("ا", s)
    s = s.replace(_ALEF_MAKSURA, "ي")
    s = s.translate(_AR_DIGITS).translate(_EAST_AR_DIGITS)
    s = _WHITESPACE.sub(" ", s)
    return s.lower().strip()


class ItemSynonym(models.Model):
    """صياغة بديلة (مرادف) لبند كنسي.

    تتراكم من جداول الكميات الواردة من جهات حكومية مختلفة. كل صياغة
    تربط بـ canonical_item_id ولا تتكرر بصياغتها المُطبَّعة لنفس البند.
    """

    _name = "rawasi.item.synonym"
    _description = "مرادف بند (Item Synonym)"
    _order = "frequency desc, last_seen_date desc"

    canonical_item_id = fields.Many2one(
        "rawasi.item.master", string="البند الكنسي",
        required=True, ondelete="cascade", index=True,
    )
    text_raw = fields.Char(string="النص الخام", required=True)
    text_normalized = fields.Char(
        string="النص المُطبَّع",
        compute="_compute_normalized", store=True, index=True,
    )
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
        help="الجهة الحكومية التي ظهرت هذه الصياغة في وثائقها (اختياري).",
    )
    frequency = fields.Integer(string="تكرار الظهور", default=1)
    first_seen_date = fields.Date(
        string="أول ظهور", default=fields.Date.context_today,
    )
    last_seen_date = fields.Date(
        string="آخر ظهور", default=fields.Date.context_today, index=True,
    )
    confidence_score = fields.Float(
        string="درجة الثقة", default=1.0,
        help="من 0 إلى 1 — مدى اليقين بالربط بالبند الكنسي.",
    )

    # عمود embedding من post_init_hook (vector(1024)) — وصول SQL مباشر.

    _text_canonical_uniq = models.Constraint(
        "UNIQUE(canonical_item_id, text_normalized)",
        "لا يمكن تكرار نفس الصياغة المُطبَّعة لنفس البند الكنسي.",
    )

    @api.depends("text_raw")
    def _compute_normalized(self):
        for rec in self:
            rec.text_normalized = normalize_arabic(rec.text_raw or "")
