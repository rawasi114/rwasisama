# -*- coding: utf-8 -*-
"""الصياغة البديلة — Item Variant.

كل صياغة خام من ملف اعتماد تربط ببند مرجعي واحد. تتراكم مع كل استيراد
وتصبح المادة الأولية لمحرك المطابقة (المستوى الأول: تطابق نصي كامل).
"""
import re

from odoo import api, fields, models


# تطبيع التشكيل والتطويل والهمزات والأرقام لأجل المطابقة.
# ملاحظة: نُحدِّد نطاق التشكيل بدقة (U+064B–U+065F + U+0670 + علامات
# المصحف U+06D6–U+06ED + التطويل U+0640). النطاق الفضفاض U+064B–U+0670
# الذي كان مستخدماً يبتلع أرقام U+0660–U+0669 (٠–٩) لأنها تقع داخله،
# فيُتلف كل قياس عربي مثل "٦٠×٦٠" → "×".
_TASHKEEL = re.compile(
    "[ً-ٰٟۖ-ۭـ]"
)
_LIGHT_HAMZA = str.maketrans({"آ": "ا", "أ": "ا", "إ": "ا", "ى": "ي", "ة": "ه"})
_AR_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_EAST_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def normalize_for_matching(text):
    """تطبيع كامل لنص لأغراض المطابقة (Auto-Normalization)."""
    if not text:
        return ""
    s = str(text).strip()
    s = _TASHKEEL.sub("", s)
    s = s.translate(_LIGHT_HAMZA)
    s = s.translate(_AR_DIG).translate(_EAST_DIG)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


class ItemVariant(models.Model):
    _name = "rawasi.item.variant"
    _description = "صياغة بديلة — Item Variant"
    _order = "frequency desc, last_seen_date desc"

    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي",
        required=True, ondelete="cascade", index=True,
    )
    original_text = fields.Char(
        string="الوصف كما ورد", required=True,
        help="النص الأصلي كما ورد في كراسة اعتماد، يحفظ بدون أي تعديل.",
    )
    normalized_text = fields.Char(
        string="النص المُوحَّد",
        compute="_compute_normalized", store=True, index=True,
    )
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
        help="الجهة الحكومية التي ظهرت فيها هذه الصياغة (اختياري).",
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
        help="من 0 إلى 1 — مدى اليقين بالربط بالبند المرجعي.",
    )

    _variant_uniq = models.Constraint(
        "UNIQUE(reference_item_id, normalized_text)",
        "لا يمكن تكرار نفس الصياغة المُوحَّدة لنفس البند المرجعي.",
    )

    @api.depends("original_text")
    def _compute_normalized(self):
        for rec in self:
            rec.normalized_text = normalize_for_matching(rec.original_text or "")
