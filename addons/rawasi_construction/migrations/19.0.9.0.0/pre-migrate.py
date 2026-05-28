# -*- coding: utf-8 -*-
"""قبل تحديث Odoo: تجهيز قاعدة البيانات لاستيعاب موديول الكتالوج المدموج.

السيناريو: في إصدارات سابقة كان كتالوج البنود موديولاً منفصلاً
(rawasi_item_catalog). الآن جرى دمجه داخل rawasi_construction. هذا السكربت
يضمن:

1. وجود امتداد pgvector (تحتاجه أعمدة embedding التي ستُنشأ في post-migrate).
2. نقل ملكية كل سجلات ir.model.data من rawasi_item_catalog إلى
   rawasi_construction قبل أن تحاول ملفات data الجديدة إيجاد السجلات
   الموجودة بنفس XML IDs. بدون هذا النقل، loader سيظنّ أن السجلات غير
   موجودة ويحاول إنشاء مكرَّرات → خرق UNIQUE constraints.

كل الأوامر idempotent — يمكن تشغيلها مرّات دون ضرر.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # 1. pgvector
    cr.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    _logger.info("rawasi_construction: pgvector extension ensured")

    # 2. نقل ملكية ir.model.data من rawasi_item_catalog
    cr.execute("""
        SELECT COUNT(*) FROM ir_model_data
        WHERE module = 'rawasi_item_catalog'
    """)
    count = cr.fetchone()[0]
    if count:
        cr.execute("""
            UPDATE ir_model_data
            SET module = 'rawasi_construction'
            WHERE module = 'rawasi_item_catalog'
        """)
        _logger.info(
            "rawasi_construction: re-parented %d ir.model.data rows "
            "from rawasi_item_catalog → rawasi_construction", count
        )
    else:
        _logger.info(
            "rawasi_construction: no rawasi_item_catalog records to re-parent "
            "(either fresh install or already merged)"
        )
