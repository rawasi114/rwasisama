# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — المنافسات والتسعير",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "موديول المكتب الفني: المنافسات، التسعير، ذاكرة الأسعار، سجل البنود المرجعي. المنافسات الخاسرة تبقى هنا أرشيفاً.",
    "description": """
موديول مستقل للمكتب الفني (التسعير ودراسة المنافسات).

يُعيد ترتيب واجهة قوائم المنافسات والتسعير وذاكرة الأسعار وسجل البنود
المرجعي تحت تطبيق مستقل، فيظهر المكتب الفني كنظام منفصل عن إدارة
المقاولات (التي تركّز على المشاريع التنفيذية فقط).

السلوك:
- المنافسات الخاسرة (action_lost) تبقى أرشيفاً للمكتب الفني هنا
- المنافسات الفائزة (action_won) تُنشئ مشروعاً تلقائياً في موديول
  المقاولات (سلوك قائم — لا تغيير)
""",
    "author": "Rawasi Sama",
    "website": "https://rawasi-sama.sa",
    "license": "LGPL-3",
    "depends": ["rawasi_construction"],
    "data": [
        "security/rawasi_competitions_security.xml",
        "views/rawasi_competitions_menus.xml",
    ],
    "installable": True,
    "application": True,
}
