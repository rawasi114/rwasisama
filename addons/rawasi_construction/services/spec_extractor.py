# -*- coding: utf-8 -*-
"""مستخلص المواصفات الفنية — يقرأ نص بند BOQ ويستخرج بـ regex:

- الأبعاد: 60×60، 600x600، 100*100
- السماكة: سمك 10 سم، سماكة 5 مم، سمك 100مم
- القطر: قطر 50 مم، Ø 110، diameter 200mm
- الجهد/المقاومة: جهد 25 نيوتن/مم2، C30، C35
"""
import re


# ── Dimensions ─────────────────────────────────────────────────
_DIM_PATTERN = re.compile(
    r"(\d{1,4})\s*[×x\*]\s*(\d{1,4})(?:\s*[×x\*]\s*(\d{1,4}))?",
    re.IGNORECASE,
)

def extract_dimensions(text):
    if not text:
        return None
    m = _DIM_PATTERN.search(text)
    if not m:
        return None
    parts = [g for g in m.groups() if g]
    return "x".join(parts)


# ── Thickness ───────────────────────────────────────────────────
_THICK_PATTERN = re.compile(
    r"(?:سمك|سماكة|سما|thickness|thk)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(سم|مم|cm|mm|m)?",
    re.IGNORECASE,
)

def extract_thickness(text):
    if not text:
        return None
    m = _THICK_PATTERN.search(text)
    if not m:
        return None
    val, unit = m.group(1), (m.group(2) or "مم").strip()
    return f"{val} {unit}"


# ── Diameter ────────────────────────────────────────────────────
_DIAM_PATTERN = re.compile(
    r"(?:قطر|Ø|diameter|dia)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(سم|مم|cm|mm|m|بوصة|inch|\"|in)?",
    re.IGNORECASE,
)

def extract_diameter(text):
    if not text:
        return None
    m = _DIAM_PATTERN.search(text)
    if not m:
        return None
    val, unit = m.group(1), (m.group(2) or "مم").strip()
    return f"{val} {unit}"


# ── Concrete strength (e.g., جهد 25 نيوتن/مم2، C30) ─────────────
_STRENGTH_PATTERN_AR = re.compile(
    r"(?:جهد|قوة|مقاومة)\s*[:\-]?\s*\(?(\d+)\)?\s*(?:نيوتن/مم2|N/mm2|MPa|ميجا باسكال)?",
    re.IGNORECASE,
)
_STRENGTH_PATTERN_EN = re.compile(r"\bC\s*(\d{2,3})\b")

def extract_strength(text):
    if not text:
        return None
    m = _STRENGTH_PATTERN_AR.search(text) or _STRENGTH_PATTERN_EN.search(text)
    if not m:
        return None
    return f"{m.group(1)} N/mm²"


# ── Convenience ─────────────────────────────────────────────────
def extract_all(text):
    return {
        "dimensions": extract_dimensions(text),
        "thickness": extract_thickness(text),
        "diameter": extract_diameter(text),
        "strength": extract_strength(text),
    }
