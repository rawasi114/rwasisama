# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — Workshop",
    "summary": "إدارة الورشة: الأقسام، أوامر التصنيع، بوابات الدفع، تكامل البيع",
    "description": "موديول إدارة الورشة لنظام رواسي سما.",
    "category": "Rawasi/Workshop",
    "version": "19.0.1.0.1",
    "author": "Rawasi Sama Contracting",
    "website": "https://www.rawasisama.com",
    "license": "LGPL-3",
    "depends": [
        "rawasi_base",
        "sale_management",
        "stock_account",
    ],
    "data": [
        # Security
        "security/groups.xml",
        "security/ir.model.access.csv",
        # Master data
        "data/sequences.xml",
        "data/workshop_data.xml",
        # Menus (root first)
        "views/menu_root.xml",
        # Views
        "views/section_views.xml",
        "views/workshop_mo_views.xml",
        "views/workshop_material_request_views.xml",
        "views/sale_order_views.xml",
    ],
    "application": True,
    "installable": True,
}
