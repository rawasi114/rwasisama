# -*- coding: utf-8 -*-
"""ترحيل قبل الترقية.

عند ترقية الموديول، قد تحتوي قاعدة البيانات على نسخ قديمة من عروض نموذج
المشروع/الشركة تشير إلى حقول أُعيدت تسميتها (document_count → rawasi_document_count
و mas_count → rawasi_mas_count ...) أو حُقول حُذفت (ختم الشركة الملغى). يتحقّق
أودو من العروض الموروثة أثناء التحميل، فتفشل الترقية بسبب «الحقل غير موجود».

نحذف هذه العروض هنا (قبل تحميل XML) لتُعاد إنشاؤها نظيفة من الإصدار الجديد.
"""

STALE_VIEW_XMLIDS = (
    "view_project_form_rawasi_wbs",
    "view_project_form_rawasi_phase4",
    "view_company_form_rawasi_stamp",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'rawasi_construction'
          AND model = 'ir.ui.view'
          AND name IN %s
        """,
        (STALE_VIEW_XMLIDS,),
    )
    view_ids = tuple(row[0] for row in cr.fetchall())
    if view_ids:
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (view_ids,))
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'rawasi_construction'
          AND model = 'ir.ui.view'
          AND name IN %s
        """,
        (STALE_VIEW_XMLIDS,),
    )
