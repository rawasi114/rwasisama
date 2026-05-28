# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — كتالوج البنود (مدموج في موديول المقاولات)",
    "version": "19.0.5.0.0",
    "category": "Hidden",
    "summary": "Stub — catalog merged into rawasi_construction. Do not install.",
    "description": """
        ⚠️ هذا الموديول تم دمجه داخل rawasi_construction.

        كل النماذج (rawasi.item.master، rawasi.item.taxonomy، إلخ.)
        والبيانات (الـ 519 بنداً + شجرة التصنيف + المرادفات) موجودة الآن
        تحت موديول رواسي سما — إدارة الإنشاءات والمقاولات.

        التثبيت معطَّل لمنع الاستخدام الجديد. الموديولات المثبَّتة سابقاً
        ستجد بياناتها سليمة بعد ترقية rawasi_construction (سكربت الترقية
        ينقل ملكية ir.model.data تلقائياً).
    """,
    "author": "Rawasi Sama Contracting",
    "website": "https://rawasi-sama.sa",
    "license": "LGPL-3",
    "depends": ["rawasi_construction"],
    "data": [],
    "installable": False,
    "application": False,
    "auto_install": False,
}
