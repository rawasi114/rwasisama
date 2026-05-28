# -*- coding: utf-8 -*-
"""موحِّد وحدات القياس — يحوّل الـ 13 صياغة شائعة الورود في ملفات اعتماد
إلى 5 وحدات معتمدة في النظام:

  م2 (Square Meter), م3 (Cubic Meter), م.ط (Linear Meter), عدد (Each), كجم (Kg)
"""
import re


# ── خرائط التوحيد ───────────────────────────────────────────────
_UNIT_MAP = {
    # square meter
    "م²": "SQM", "م2": "SQM", "م 2": "SQM", "مترمربع": "SQM",
    "متر مربع": "SQM", "م. مربع": "SQM", "م مربع": "SQM",
    "sqm": "SQM", "sq m": "SQM", "sq.m": "SQM", "m2": "SQM",
    # cubic meter
    "م3": "CBM", "م³": "CBM", "م 3": "CBM", "متر مكعب": "CBM",
    "مترمكعب": "CBM", "م. مكعب": "CBM", "m3": "CBM", "cbm": "CBM",
    "م4": "CBM",  # شائع كخطأ مطبعي
    # linear meter
    "م.ط": "MTR", "م ط": "MTR", "م . ط": "MTR", "م/ط": "MTR",
    "م-ط": "MTR", "متر": "MTR", "متر طولي": "MTR", "م طولي": "MTR",
    "lm": "MTR", "ml": "MTR", "mtr": "MTR",
    # each / count
    "عدد": "EA", "رقم": "EA", "وحدة": "EA", "ec": "EA", "ea": "EA",
    "pcs": "EA", "pc": "EA",
    # weight (kg)
    "كجم": "KG", "كغ": "KG", "كيلو": "KG", "كيلوغرام": "KG",
    "كيلوجرام": "KG", "kg": "KG",
    # set / system → treat as each
    "مجموعة": "EA", "نظام": "EA", "طقم": "EA", "set": "EA",
}


# ── XML IDs للوحدات المُنشَأة في data/uom_extra_data.xml ────────
_UNIT_XMLID = {
    "SQM": "rawasi_construction.uom_sqm",
    "CBM": "rawasi_construction.uom_cbm",
    "MTR": "rawasi_construction.uom_mtr",
    "EA":  "uom.product_uom_unit",
    "KG":  "uom.product_uom_kgm",
}


def _clean(text):
    if not text:
        return ""
    s = str(text).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_unit_code(raw):
    """يرجع كود الوحدة المُوحَّد (SQM/CBM/MTR/EA/KG) أو None لو لم يُتعرَّف."""
    c = _clean(raw)
    if not c:
        return None
    return _UNIT_MAP.get(c)


def get_uom_record(env, raw):
    """يرجع سجل uom.uom المقابل للنص الخام، أو uom.product_uom_unit افتراضياً."""
    code = normalize_unit_code(raw)
    if not code:
        return env.ref("uom.product_uom_unit", raise_if_not_found=False)
    xmlid = _UNIT_XMLID[code]
    rec = env.ref(xmlid, raise_if_not_found=False)
    if not rec:
        rec = env.ref("uom.product_uom_unit", raise_if_not_found=False)
    return rec
