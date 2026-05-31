# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — Construction",
    "summary": "إدارة المقاولات: المنافسات، جداول الكميات، المشاريع، الكتالوج، قوائم المواد",
    "category": "Rawasi/Construction",
    "version": "19.0.1.0.0",
    "author": "Rawasi Sama Contracting",
    "website": "https://www.rawasisama.com",
    "license": "LGPL-3",
    "depends": [
        "rawasi_base",
        "project",
        "stock_account",
    ],
    "data": [
        # Security
        "security/groups.xml",
        "security/ir.model.access.csv",
        # Master data
        "data/sequences.xml",
        # Menus (root first)
        "views/menu_root.xml",
        # Views
        "views/reference_item_views.xml",
        "views/competition_views.xml",
        "views/project_views.xml",
        "views/bom_views.xml",
    ],
    "application": True,
    "installable": True,
}
