# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — Integration (Internal Workshop)",
    "summary": "التكامل بين المقاولات والورشة: التصنيع الداخلي + النقل التلقائي + اللوحة الموحدة",
    "description": "موديول التكامل (التصنيع الداخلي) لنظام رواسي سما.",
    "category": "Rawasi",
    "version": "19.0.1.0.1",
    "author": "Rawasi Sama Contracting",
    "website": "https://www.rawasisama.com",
    "license": "LGPL-3",
    "depends": [
        "rawasi_construction",
        "rawasi_workshop",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "views/internal_workshop_order_views.xml",
        "views/material_request_views.xml",
        "views/dashboard_views.xml",
    ],
    "application": True,
    "installable": True,
}
