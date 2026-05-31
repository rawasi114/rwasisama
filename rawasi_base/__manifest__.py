# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — Base",
    "summary": "الأساس المشترك لنظام رواسي سما (هوية، مجموعات، حسابات، أصول، إشعارات، DMS، تدقيق، اعتماد)",
    "category": "Rawasi",
    "version": "19.0.1.0.0",
    "author": "Rawasi Sama Contracting",
    "website": "https://www.rawasisama.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
        "sms",
        "uom",
        "product",
        "stock",
        "purchase",
        "account",
        "analytic",
        "sale",
        "hr",
    ],
    "data": [
        # Security (foundational — shared across all rawasi modules)
        "security/groups.xml",
        "security/ir.model.access.csv",
        # Accounting master data
        "data/rawasi_analytic_plans.xml",
        "data/rawasi_chart_of_accounts.xml",
        # Equipment (fixed assets)
        "data/equipment_sequence.xml",
        # Automation
        "data/cron.xml",
        # Visual identity
        "report/paperformat.xml",
        "report/rawasi_layout.xml",
        "data/rawasi_brand_defaults.xml",
        # Wizards
        "wizard/pin_wizard_views.xml",
        # Menus & views
        "views/menu_root.xml",
        "views/equipment_views.xml",
        "views/document_views.xml",
        "views/audit_trail_views.xml",
        "views/approval_chain_views.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "rawasi_base/static/src/scss/rawasi_theme.scss",
        ],
        "web.report_assets_common": [
            "rawasi_base/static/src/scss/rawasi_report.scss",
        ],
    },
    "application": False,
    "installable": True,
}
