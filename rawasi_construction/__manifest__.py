# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — Construction",
    "summary": "إدارة المقاولات: المنافسات، جداول الكميات، المشاريع، المستخلصات، الضمانات",
    "description": "موديول إدارة المقاولات لنظام رواسي سما.",
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
        "data/cron.xml",
        "data/rawasi.lcgpa.code.csv",
        # Menus (root first)
        "views/menu_root.xml",
        # Views
        "views/reference_item_views.xml",
        "views/classification_views.xml",
        "views/price_intelligence_views.xml",
        "views/import_batch_views.xml",
        "views/competition_views.xml",
        "views/project_views.xml",
        "views/bom_views.xml",
        "views/material_request_views.xml",
        "views/site_report_views.xml",
        "views/variation_order_views.xml",
        "views/material_approval_views.xml",
        "views/subcontract_views.xml",
        "views/wbs_activity_views.xml",
        "views/ipc_views.xml",
        "views/bank_guarantee_views.xml",
    ],
    "application": True,
    "installable": True,
}
