# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — كتالوج البنود الموحَّد",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "Master item catalog: taxonomy, canonical items, synonyms, attributes, semantic search (pgvector)",
    "description": """
        كتالوج البنود الموحَّد لشركة رواسي سما للمقاولات.

        الهدف الاستراتيجي: تحويل النصوص الخام لجداول الكميات (~25,000 صياغة بديلة سنوياً)
        إلى ~5,000 بند كنسي موحَّد قابل للاستعلام والتحليل.

        المكوّنات:
        - تصنيف شجري هرمي (4 مستويات: شعبة → قسم → فئة → فئة فرعية)
        - بنود كنسية بأكواد فريدة (XXX-XXX-XXXX-NNN)
        - جدول مرادفات قابل للتوسعة لربط الصياغات الخام
        - خصائص منظَّمة قابلة للاستعلام
        - دعم البحث الدلالي عبر pgvector (HNSW + cosine)
        - سجل تدقيق لكل عملية تطبيع

        مرحلة الإطلاق: Phase 0 — هيكل الموديول فقط، لا منطق أعمال.
    """,
    "author": "Rawasi Sama Contracting",
    "website": "https://rawasi-sama.sa",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "uom",
    ],
    "external_dependencies": {
        # pgvector is verified via pre-init.py (CREATE EXTENSION).
        # Python client lib is not required at this phase — embeddings are
        # populated in a later phase outside this module's scope.
    },
    "data": [
        # Intentionally empty in Phase 0. Security, views, and seed data
        # land in Phase 1 / Phase 2 behind explicit CEO approval gates.
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
