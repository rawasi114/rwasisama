{
    "name": "Award Radar — رادار الترسية",
    "version": "1.0.0",
    "category": "Sales/Contracting",
    "summary": "رادار الترسية: استخبارات تنافسية للمنافسات الحكومية السعودية",
    "description": """
رادار الترسية (Award Radar)
============================

منصة استخبارات تنافسية متكاملة لمنافسات القطاع الحكومي السعودي.

الميزات الرئيسية:
- قاعدة بيانات الترسيات والمنافسين
- استخراج جداول الكميات تلقائياً عبر Claude API
- محرك تسعير مرجعي للبنود
- تحليل المنافسين وأنماط تسعيرهم
- حساب احتمالية الفوز
- أداة Go/No-Go لقرار الدخول الذكي
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
