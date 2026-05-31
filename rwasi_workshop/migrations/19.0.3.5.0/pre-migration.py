# -*- coding: utf-8 -*-
"""دمج أوامر التصنيع المتعددة لكل أمر بيع في أمر تصنيع واحد (1:1).

السياق: قبل هذه النسخة، كان تأكيد أمر بيع يُنشئ أمر تصنيع منفصل لكل بند منتج
ورشي. النموذج الجديد يفرض 1:1 — أمر بيع واحد له أمر تصنيع واحد فقط، وبنود
المنتجات الورشية المتعددة تصبح بنود تنفيذ (work jobs) داخل ذلك الأمر.

هذا السكربت يعالج البيانات القائمة:
  1) لكل أمر بيع له أكثر من MO: اختيار الأقدم (أصغر id) كـ primary
  2) لكل MO ثانوي:
     - تحويل MO نفسه إلى work_order_line (سطر تنفيذ) داخل primary، يحفظ
       product_id و qty و scope_of_work كـ description
     - نقل أسطر التنفيذ الموجودة في MO الثانوي إلى primary
     - نقل أسطر المواد إلى primary
     - تحويل purchase.order.workshop_order_id إلى primary
     - تحويل closeout/quality/rework FKs إلى primary
     - حذف MO الثانوي

يُنفَّذ قبل ترقية الـ schema (pre-migration) لأن SQL UNIQUE constraint
الجديد على sale_order_id سيمنع الترقية لو كانت البيانات بها تعارض.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # ابحث عن أوامر البيع التي لها أكثر من MO
    cr.execute("""
        SELECT sale_order_id, MIN(id) AS primary_id, array_agg(id) AS all_ids
          FROM rwasi_work_order
         WHERE sale_order_id IS NOT NULL
         GROUP BY sale_order_id
        HAVING COUNT(*) > 1
    """)
    rows = cr.fetchall()
    if not rows:
        _logger.info("RAWASI WORKSHOP MIGRATION 19.0.3.5.0: لا توجد MOs مكرّرة "
                     "لنفس أمر البيع — لا حاجة للدمج.")
        return

    _logger.info(
        "RAWASI WORKSHOP MIGRATION 19.0.3.5.0: سيتم دمج %s أمر بيع لها MOs متعددة.",
        len(rows),
    )

    # تحقق من وجود حقل sale_line_id على MO header (موجود في الـ schema القديم
    # قبل هذه النسخة، محذوف بعدها). نقرأه لنحفظه في الـ work job المنشَأ.
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'rwasi_work_order'
           AND column_name = 'sale_line_id'
    """)
    has_old_sale_line = bool(cr.fetchone())

    total_secondary = 0
    for sale_order_id, primary_id, all_ids in rows:
        secondary_ids = [i for i in all_ids if i != primary_id]
        total_secondary += len(secondary_ids)

        # 1) ابنِ بنود تنفيذ (work_jobs) من كل MO ثانوي تمثّل المنتج الذي
        #    كان يُصنَّع في ذلك MO، ثم ضعها داخل primary
        for sec_id in secondary_ids:
            if has_old_sale_line:
                cr.execute("""
                    SELECT product_id, product_qty, scope_of_work, sale_line_id
                      FROM rwasi_work_order WHERE id = %s
                """, (sec_id,))
            else:
                cr.execute("""
                    SELECT product_id, product_qty, scope_of_work, NULL::int
                      FROM rwasi_work_order WHERE id = %s
                """, (sec_id,))
            sec = cr.fetchone()
            if not sec:
                continue
            product_id, product_qty, scope, sale_line_id = sec

            description = (scope or '').strip() or 'بند مُحوَّل من MO سابق'
            cr.execute("""
                INSERT INTO rwasi_work_order_line
                    (order_id, sale_line_id, product_id, sequence,
                     description, qty)
                VALUES (%s, %s, %s, 90, %s, %s)
            """, (primary_id, sale_line_id, product_id,
                  description[:255], product_qty or 1.0))

        secondary_tuple = tuple(secondary_ids)

        # 2) انقل أسطر التنفيذ الموجودة سلفاً في الـ MOs الثانوية إلى primary
        cr.execute("""
            UPDATE rwasi_work_order_line
               SET order_id = %s
             WHERE order_id IN %s
        """, (primary_id, secondary_tuple))

        # 3) انقل أسطر المواد إلى primary
        cr.execute("""
            UPDATE rwasi_work_order_material
               SET order_id = %s
             WHERE order_id IN %s
        """, (primary_id, secondary_tuple))

        # 4) انقل purchase orders
        cr.execute("""
            UPDATE purchase_order
               SET workshop_order_id = %s
             WHERE workshop_order_id IN %s
        """, (primary_id, secondary_tuple))

        # 5) انقل closeout (إن وُجد جدول)
        cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'rwasi_project_closeout'
               AND column_name = 'work_order_id'
        """)
        if cr.fetchone():
            cr.execute("""
                UPDATE rwasi_project_closeout
                   SET work_order_id = %s
                 WHERE work_order_id IN %s
            """, (primary_id, secondary_tuple))

        # 6) انقل quality reports
        cr.execute("""
            SELECT 1 FROM information_schema.tables
             WHERE table_name = 'rwasi_qc_report'
        """)
        if cr.fetchone():
            cr.execute("""
                UPDATE rwasi_qc_report
                   SET work_order_id = %s
                 WHERE work_order_id IN %s
            """, (primary_id, secondary_tuple))

        # 7) انقل rework orders
        cr.execute("""
            SELECT 1 FROM information_schema.tables
             WHERE table_name = 'rwasi_rework_order'
        """)
        if cr.fetchone():
            cr.execute("""
                UPDATE rwasi_rework_order
                   SET work_order_id = %s
                 WHERE work_order_id IN %s
            """, (primary_id, secondary_tuple))

        # 8) أزل أي إشارة من primary إلى نفسه عبر closeout_id (لو كان يشير
        #    لإغلاق تابع لـ MO ثانوي، احتفظ به — الإغلاق الآن مرتبط بـ primary)
        # لا داعي لتغيير closeout_id على primary

        # 9) احذف الـ MOs الثانوية (mail messages/activities ستُحذف cascade)
        cr.execute("""
            DELETE FROM rwasi_work_order
             WHERE id IN %s
        """, (secondary_tuple,))

    _logger.info(
        "RAWASI WORKSHOP MIGRATION 19.0.3.5.0: تم دمج %s MO ثانوي في %s primary.",
        total_secondary, len(rows),
    )
