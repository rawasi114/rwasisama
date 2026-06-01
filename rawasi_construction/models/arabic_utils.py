# -*- coding: utf-8 -*-
"""أدوات تطبيع النص العربي — تُستخدم في ذاكرة الأسعار ومطابقة استيراد جدول الكميات.

ثلاثة مستويات:
- ``normalize_light``: تطبيع خفيف للعناوين/الأوصاف (يحافظ على المسافات الداخلية).
- ``normalize_unit``: تطبيع قوي لرموز الوحدات (يزيل الترقيم وكل المسافات).
- ``normalize_match``: تطبيع قوي للمطابقة الفجوية (يزيل التشكيل والترقيم، يوحّد الهمزات والحالة).
"""
import re

# توحيد أشكال الهمزة والألف والياء والتاء المربوطة
_LIGHT_HAMZA = str.maketrans({"آ": "ا", "أ": "ا", "إ": "ا", "ى": "ي", "ة": "ه"})

# التشكيل والتطويل (للتطبيع القوي)
_TASHKEEL = re.compile("[\u0610-\u061a\u064b-\u0652\u0670\u0640]")


def normalize_light(text):
    """تطبيع خفيف للعناوين والأوصاف (يحافظ على المسافات الداخلية)."""
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text.translate(_LIGHT_HAMZA)


def normalize_unit(text):
    """تطبيع قوي لرموز الوحدات: يزيل الترقيم وكل المسافات ويوحّد الهمزات."""
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[._/\-]", " ", text)
    text = text.lower()
    text = text.translate(_LIGHT_HAMZA)
    return re.sub(r"\s+", "", text)


def normalize_match(text):
    """تطبيع قوي لأوصاف البنود لأجل المطابقة الفجوية."""
    if not text:
        return ""
    text = str(text).strip().lower()
    text = _TASHKEEL.sub("", text)
    text = text.translate(_LIGHT_HAMZA)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
