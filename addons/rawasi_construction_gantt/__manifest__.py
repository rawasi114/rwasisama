# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — مخطط جانت (Gantt)",
    "version": "19.0.1.0.1",
    "category": "Services/Project",
    "summary": "عرض Gantt لأنشطة WBS (يتطلب web_gantt من Enterprise)",
    "description": "موديول جسر يضيف عرض مخطط جانت لأنشطة WBS. يعتمد على web_gantt المتوفر في Odoo Enterprise.",
    "author": "Rawasi Sama",
    "license": "LGPL-3",
    "depends": [
        "rawasi_construction",
        "web_gantt",
    ],
    "data": [
        "views/wbs_gantt_views.xml",
    ],
    "application": False,
    "installable": True,
}
