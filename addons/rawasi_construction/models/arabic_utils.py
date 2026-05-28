# -*- coding: utf-8 -*-
"""أدوات تطبيع النص العربي — قلب الاستيراد الذكي ومطابقة الوحدات والأسعار.

مطابقة لمنطق SPEC الملحق أ.٥ و أ.٨. تُستخدم في:
- مطابقة عناوين الأعمدة (Header-Based matching) بعد تطبيع خفيف.
- مطابقة رموز الوحدات بعد تطبيع قوي.
- مطابقة أوصاف البنود في الذكاء التسعيري (normalize_match).
"""
import re

_LIGHT_HAMZA = str.maketrans({"آ": "ا", "أ": "ا", "إ": "ا", "ى": "ي", "ة": "ه"})

# التشكيل والتطويل (Arabic diacritics + tatweel) للتطبيع القوي في مطابقة الأوصاف
_TASHKEEL = re.compile("[ؐ-ًؚ-ٰٟـ]")


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


def normalize_match(text):
    """تطبيع قوي لأوصاف البنود لأجل المطابقة الفجوية (Fuzzy Matching).

    يزيل التشكيل والتطويل وعلامات الترقيم، ويوحّد الهمزات وحالة الأحرف،
    ويبقي الكلمات مفصولة بمسافة واحدة (مناسب لمقارنة التشابه).
    """
    if not text:
        return ""
    text = str(text).strip().lower()
    text = _TASHKEEL.sub("", text)
    text = text.translate(_LIGHT_HAMZA)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── التوحيد الكامل لنص الصياغات البديلة ─────────────────────────
_AR_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_EAST_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def normalize_text(text):
    """تطبيع كامل لنص بند، يستخدمه `rawasi.item.variant.normalized_text`.

    خطوات: إزالة التشكيل والتطويل، توحيد الألف/الياء/التاء المربوطة،
    تحويل الأرقام العربية والفارسية إلى لاتينية، تحويل الأحرف اللاتينية
    إلى صغير، طي المسافات. يبقي التاء المربوطة على حالها لأن المصطلحات
    الفنية أحياناً تعتمد على التمييز (ساعة/ساعه).
    """
    if not text:
        return ""
    s = str(text).strip()
    s = _TASHKEEL.sub("", s)
    s = s.translate(_LIGHT_HAMZA)
    s = s.translate(_AR_DIG).translate(_EAST_DIG)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()
