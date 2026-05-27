"""Arabic-text normalization helpers."""

from __future__ import annotations

import re
import unicodedata

_TASHKEEL = re.compile(r"[ً-ٰٟۖ-ۭ]")
_TATWEEL = re.compile(r"ـ+")
_MULTI_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[،؛؟!.,;:?\\/\\(\\)\\[\\]\\{\\}\"'`]")


_ALIASES: dict[str, str] = {
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ى": "ي",
    "ئ": "ي",
    "ؤ": "و",
    "ة": "ه",
    "گ": "ك",
    "ﭺ": "چ",
}


def normalize_arabic(text: str) -> str:
    """Normalize an Arabic string for matching purposes.

    - Strips diacritics (tashkeel) and tatweel.
    - Normalizes alif/ya/ta-marbuta variants.
    - Collapses whitespace and strips punctuation.
    - Lowercases Latin characters.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = _TASHKEEL.sub("", text)
    text = _TATWEEL.sub("", text)

    for src, dst in _ALIASES.items():
        text = text.replace(src, dst)

    text = _PUNCT.sub(" ", text)
    text = _MULTI_WS.sub(" ", text)
    return text.strip().lower()


_UNIT_ALIASES: dict[str, str] = {
    # Keys MUST be in normalize_arabic() canonical form
    "م3": "m3",
    "م³": "m3",
    "متر مكعب": "m3",
    "م2": "m2",
    "م²": "m2",
    "متر مربع": "m2",
    "م ط": "m",
    "متر طولي": "m",
    "متر": "m",
    "طن": "ton",
    "كجم": "kg",
    "كغ": "kg",
    "كيلوجرام": "kg",
    "عدد": "no",
    "نمره": "no",
    "قطعه": "no",
    "وحده": "no",
    "ل س": "lump",
    "مقطوعيه": "lump",
}


def normalize_unit(unit: str | None) -> str:
    """Normalize a unit of measure to its canonical short code."""
    if not unit:
        return ""
    cleaned = normalize_arabic(unit)
    return _UNIT_ALIASES.get(cleaned, cleaned)


def units_compatible(a: str | None, b: str | None) -> bool:
    """Two units are compatible if their normalized forms are equal."""
    return normalize_unit(a) == normalize_unit(b)
