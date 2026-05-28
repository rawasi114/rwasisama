# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — كتالوج البنود الموحَّد",
    "version": "19.0.1.1.1",
    "category": "Services/Project",
    "summary": "Master item catalog: taxonomy, canonical items, synonyms, attributes, semantic search (pgvector)",
    "description": """
        كتالوج البنود الموحَّد لشركة رواسي سما للمقاولات.

        Phase 1: 5 نماذج كاملة + 3 مجموعات أمان + بذر الشعب الخمس
        + 1024-dim embedding columns عبر post-init hook.
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
    ],
    "pre_init_hook": "_pre_init_hook",
    "post_init_hook": "_post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
