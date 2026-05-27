{
    "name": "Rawasi Pricing Intelligence",
    "version": "1.0.0",
    "category": "Sales/Contracting",
    "summary": "Intelligent pricing system for Saudi government tenders",
    "description": """
نظام متكامل للذكاء التسعيري في المنافسات الحكومية:
- قاعدة بيانات الترسيات والمنافسين
- استخراج جداول الكميات تلقائياً عبر Claude API
- محرك تسعير مرجعي للبنود
- تحليل المنافسين وأنماط تسعيرهم
- حساب احتمالية الفوز وأداة Go/No-Go
    """,
    "author": "Rawasi Sama Contracting",
    "website": "https://rawasisama.com",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/tender_views.xml",
        "views/competitor_views.xml",
        "views/master_item_views.xml",
        "views/analytics_dashboard.xml",
        "wizards/pricing_simulator.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
