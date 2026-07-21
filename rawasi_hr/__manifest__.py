# -*- coding: utf-8 -*-
{
    "name": "Rawasi Sama — HR",
    "summary": "الموارد البشرية لرواسي سما: نهاية الخدمة (المواد 84/85/87) وحماية الأجور (مدد/WPS)",
    "description": """
الموديول الخامس في مسار الموارد البشرية (HR-5).

يضيف قدرتين أساسيتين متوافقتين مع نظام العمل السعودي:

1. **مكافأة نهاية الخدمة** (rawasi.eos.settlement): احتساب آلي للمكافأة
   حسب المواد 84 و85 و87 من نظام العمل (نصف شهر عن كل سنة من السنوات
   الخمس الأولى، وشهر كامل عمّا بعدها، مع نسب الاستحقاق عند الاستقالة)،
   مع توليد القيد المحاسبي على حساب «مخصص مكافأة نهاية الخدمة».

2. **حماية الأجور** (rawasi.wps.batch): توليد ملف حماية الأجور (SIF)
   بصيغة مدد/WPS لدفعة رواتب شهرية، قابل للتنزيل ورفعه للبنك.
    """,
    "category": "Rawasi",
    "version": "19.0.1.1.0",
    "author": "Rawasi Sama Contracting",
    "website": "https://www.rawasisama.com",
    "license": "LGPL-3",
    "depends": [
        "rawasi_base",
        "hr",
        "account",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "data/cron.xml",
        "views/hr_employee_views.xml",
        "views/eos_settlement_views.xml",
        "views/eos_provision_views.xml",
        "views/wps_batch_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "application": False,
    "installable": True,
}
