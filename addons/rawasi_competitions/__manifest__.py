# -*- coding: utf-8 -*-
{
    "name": "رواسي سما — المكتب الفني (التسعير والحصر)",
    "version": "19.0.2.0.0",
    "category": "Services/Project",
    "summary": "تطبيق المكتب الفني للمنافسات، الدراسات، التسعير، تحليل الأسعار، والحصر.",
    "description": """
موديول مستقل للمكتب الفني (التسعير والحصر ودراسة المنافسات).

يُثبّت فصل واجهة المكتب الفني عن تطبيق المقاولات والتنفيذ. تظهر المنافسات،
الدراسات، استيراد الحصر، سجل البنود المرجعي، تحليل الأسعار، وذاكرة الأسعار
تحت تطبيق مستقل للمكتب الفني، بينما يبقى تطبيق المقاولات مخصصاً للتنفيذ.

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
