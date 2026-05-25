# -*- coding: utf-8 -*-
"""أدوات تطبيع النص العربي — قلب الاستيراد الذكي ومطابقة الوحدات.

مطابقة لمنطق SPEC الملحق أ.٥ و أ.٨. تُستخدم في:
- مطابقة عناوين الأعمدة (Header-Based matching) بعد تطبيع خفيف.
- مطابقة رموز الوحدات بعد تطبيع قوي.
"""
import re

_LIGHT_HAMZA = str.maketrans({"آ": "ا", "أ": "ا", "إ": "ا", "ى": "ي", "ة": "ه"})


def normalize_light(text):
    """تطبيع خفيف للعناوين والأوصاف (يحافظ على المسافات الداخلية)."""
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text.translate(_LIGHT_HAMZA)


def normalize_unit(text):
    """تطبيع قوي لرموز الوحدات: يزيل الترقيم وكل المسافات ويوحّد الهمزات.

    أمثلة: "م . ط" -> "مط"، "م/ط" -> "مط"، "Sq. M" -> "sqm".
    ملاحظة: "م²" و "م2" يبقيان مختلفين (يُحَلّان عبر جدول المرادفات).
    """
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[._/\-]", " ", text)
    text = text.lower()
    text = text.translate(_LIGHT_HAMZA)
    return re.sub(r"\s+", "", text)
