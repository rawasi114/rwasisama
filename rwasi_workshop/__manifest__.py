{
    'name': 'إدارة ورشة رواسي سما',
    'summary': 'إدارة عمليات ورشة رواسي سما للمقاولات (نجارة / حدادة / ألمنيوم / CNC)',
    'description': """
نظام إدارة الورشة المركزية لشركة رواسي سما للمقاولات.

يغطي الموديول دورة حياة العمل الكاملة:
عرض السعر (أمر البيع) → تأكيد → إنشاء أمر تصنيع تلقائي مرتبط بأمر البيع
→ طلب المواد → استلام المواد → بدء التصنيع → إنهاء التصنيع → التسليم وتوقيع العميل.

كما يتضمن النماذج الرسمية المعتمدة للورشة (التشغيل، التحضير والتقارير اليومية،
الحضور وبطاقات الوقت والإنتاجية، المعاينة، فحص الجودة وعدم المطابقة وإعادة الأعمال،
الصيانة، السلامة، وإغلاق المشروع).
""",
    'author': 'Rawasi Sama Contracting',
    'website': 'https://github.com/rawasi114/rwasisama',
    'category': 'Manufacturing',
    'version': '19.0.3.3.0',
    'license': 'LGPL-3',
    'depends': ['mail', 'sale_management', 'purchase', 'stock'],
    'data': [
        'security/workshop_security.xml',
        'security/ir.model.access.csv',
        'security/multicompany_rules.xml',
        'data/sequences.xml',
        'data/user_guide_data.xml',
        'views/work_order_views.xml',
        'views/daily_views.xml',
        'views/labor_views.xml',
        'views/measurement_views.xml',
        'views/quality_views.xml',
        'views/rework_views.xml',
        'views/maintenance_views.xml',
        'views/hse_views.xml',
        'views/closeout_views.xml',
        'views/performance_views.xml',
        'views/payment_views.xml',
        'views/sale_order_views.xml',
        'views/company_views.xml',
        'report/report_base.xml',
        'report/report_documents.xml',
        'report/report_actions.xml',
        'report/report_payment.xml',
        'views/user_guide_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
