# -*- coding: utf-8 -*-
"""التوحيد التلقائي — Auto-Normalization.

- مُوحِّد وحدات القياس: 13 صياغة → 5 وحدات معتمدة (SQM/CBM/MTR/EA/KG)
- مُوحِّد النصوص: إزالة التشكيل، توحيد الأرقام والهمزات والمسافات
"""
import re


# ── مُوحِّد وحدات القياس ────────────────────────────────────────
_UNIT_MAP = {
    # م²
    "م²":"SQM","م2":"SQM","م 2":"SQM","متر مربع":"SQM","مترمربع":"SQM",
    "م. مربع":"SQM","م مربع":"SQM","sqm":"SQM","sq m":"SQM","sq.m":"SQM",
    "m2":"SQM","m²":"SQM",
    # م³
    "م³":"CBM","م3":"CBM","م 3":"CBM","متر مكعب":"CBM","مترمكعب":"CBM",
    "م. مكعب":"CBM","m3":"CBM","cbm":"CBM","م4":"CBM",
    # م.ط
    "م.ط":"MTR","م ط":"MTR","م . ط":"MTR","م/ط":"MTR","م-ط":"MTR",
    "متر":"MTR","متر طولي":"MTR","م طولي":"MTR","lm":"MTR","ml":"MTR","mtr":"MTR","m":"MTR",
    # عدد
    "عدد":"EA","رقم":"EA","وحدة":"EA","ec":"EA","ea":"EA","pcs":"EA","pc":"EA","قطعة":"EA",
    "مجموعة":"EA","نظام":"EA","طقم":"EA","set":"EA",
    # كجم
    "كجم":"KG","كغ":"KG","كيلو":"KG","كيلوغرام":"KG","كيلوجرام":"KG","kg":"KG",
}
UNIT_DISPLAY = {"SQM":"م²","CBM":"م³","MTR":"م.ط","EA":"عدد","KG":"كجم"}


def normalize_unit(raw):
    """يرجع (code, display_label) أو (None, None)."""
    if not raw:
        return (None, None)
    s = re.sub(r"\s+", " ", str(raw).strip().lower())
    code = _UNIT_MAP.get(s)
    if code:
        return (code, UNIT_DISPLAY[code])
    return (None, None)


# ── مُوحِّد النصوص العامة ───────────────────────────────────────
# نطاقات دقيقة للتشكيل والتطويل (لا تلتهم حروف الأبجدية)
_TASHKEEL = re.compile(r"[ً-ٰٟۖ-ۭـ]")
_LIGHT_HAMZA = str.maketrans({"آ":"ا","أ":"ا","إ":"ا","ى":"ي","ة":"ه"})
_AR_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_EAST_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def normalize_text_full(text):
    """التطبيع الكامل: تشكيل، أرقام، همزات، مسافات، lowercase."""
    if not text:
        return ""
    s = str(text).strip()
    s = _TASHKEEL.sub("", s)
    s = s.translate(_LIGHT_HAMZA)
    s = s.translate(_AR_DIG).translate(_EAST_DIG)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()
