# -*- coding: utf-8 -*-
"""ترحيل قبل الترقية: إزالة المراحل القياسية القديمة (الخمس) ليحلّ محلّها
المراحل الرئيسية الست الجديدة (INT-01 ... CLO-06) عند تحميل البيانات.

حذف قالب المرحلة يضبط phase_id لأنشطة المشاريع القائمة على NULL (set null)،
دون حذف الأنشطة نفسها.
"""

OLD_PHASE_XMLIDS = (
    "wbs_phase_mobilization",
    "wbs_phase_structure",
    "wbs_phase_architecture",
    "wbs_phase_mep",
    "wbs_phase_handover",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'rawasi_construction'
          AND model = 'rawasi.wbs.phase'
          AND name IN %s
        """,
        (OLD_PHASE_XMLIDS,),
    )
    phase_ids = tuple(row[0] for row in cr.fetchall())
    if phase_ids:
        cr.execute("DELETE FROM rawasi_wbs_phase WHERE id IN %s", (phase_ids,))
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'rawasi_construction'
          AND model = 'rawasi.wbs.phase'
          AND name IN %s
        """,
        (OLD_PHASE_XMLIDS,),
    )
