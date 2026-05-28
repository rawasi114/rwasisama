# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — كتالوج البنود الموحَّد",
    "version": "19.0.2.0.2",
    "category": "Services/Project",
    "summary": "Master item catalog: taxonomy, canonical items, synonyms, attributes, semantic search (pgvector)",
    "description": """
        كتالوج البنود الموحَّد لشركة رواسي سما للمقاولات.

        Phase 2: واجهات كاملة لكل النماذج الخمسة + قائمة رئيسية تظهر في
        App Launcher مع أيقونة الموديول.
    """,
    "author": "Rawasi Sama Contracting",
    "website": "https://rawasi-sama.sa",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "uom",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/taxonomy_root_seed.xml",
        "views/item_taxonomy_views.xml",
        "views/item_master_views.xml",
        "views/item_synonym_views.xml",
        "views/item_mapping_audit_views.xml",
        "views/menu.xml",
    ],
    "pre_init_hook": "_pre_init_hook",
    "post_init_hook": "_post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
