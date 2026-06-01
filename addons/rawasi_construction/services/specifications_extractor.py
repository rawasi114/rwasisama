# -*- coding: utf-8 -*-
"""مستخلص المواصفات الفنية (extracted_specifications) بـ regex.

يستخرج: الأبعاد، السماكة، القطر، الجهد الخرساني — من نص وصف بند BOQ.
"""
import re


_DIM_PATTERN = re.compile(
    r"(\d{1,4})\s*[×x\*]\s*(\d{1,4})(?:\s*[×x\*]\s*(\d{1,4}))?",
    re.IGNORECASE,
)
_THICK_PATTERN = re.compile(
    r"(?:سمك|سماكة|سما|thickness|thk)\s*[:\-]?\s*\(?(\d+(?:\.\d+)?)\)?\s*(سم|مم|cm|mm|m)?",
    re.IGNORECASE,
)
_DIAM_PATTERN = re.compile(
    r"(?:قطر|Ø|diameter|dia)\s*[:\-]?\s*\(?(\d+(?:\.\d+)?)\)?\s*(سم|مم|cm|mm|m|بوصة|inch|in)?",
    re.IGNORECASE,
)
_STRENGTH_AR = re.compile(
    r"(?:جهد|قوة|مقاومة)\s*[:\-]?\s*\(?(\d+)\)?\s*(?:نيوتن/مم2|نيوتن/مم²|N/mm2|N/mm²|MPa)?",
    re.IGNORECASE,
)
_STRENGTH_EN = re.compile(r"\bC\s*(\d{2,3})\b")


def extract_dimensions(text):
    if not text: return None
    m = _DIM_PATTERN.search(text)
    if not m: return None
    parts = [g for g in m.groups() if g]
    return "x".join(parts)


def extract_thickness(text):
    if not text: return None
    m = _THICK_PATTERN.search(text)
    if not m: return None
    val, unit = m.group(1), (m.group(2) or "مم").strip()
    return f"{val} {unit}"


def extract_diameter(text):
    if not text: return None
    m = _DIAM_PATTERN.search(text)
    if not m: return None
    val, unit = m.group(1), (m.group(2) or "مم").strip()
    return f"{val} {unit}"


def extract_strength(text):
    if not text: return None
    m = _STRENGTH_AR.search(text) or _STRENGTH_EN.search(text)
    if not m: return None
    return f"{m.group(1)} N/mm²"


def extract_all(text):
    return {
        "dimensions": extract_dimensions(text),
        "thickness":  extract_thickness(text),
        "diameter":   extract_diameter(text),
        "strength":   extract_strength(text),
    }
