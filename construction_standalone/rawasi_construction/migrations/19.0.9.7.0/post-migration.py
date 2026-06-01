# -*- coding: utf-8 -*-
"""ترقية الموديول من 19.0.9.6.0 → 19.0.9.7.0

يُحمِّل شجرة حسابات رواسي + يضبط تسلسلات 10001 على DBs الإنتاجية
المُثبَّت عليها الموديول مسبقاً (حيث `post_init_hook` لا يُستدعى عند
الترقية).

العملية idempotent:
- إنشاء الحسابات يتجاوز ما هو موجود (يُسجَّل في ir.model.data)
- استدعاء generic_coa يُتجاهل إن كان chart_template مضبوطاً
- ضبط ir.sequence يحدث فقط لو number_next_actual ≤ 1
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """يُنفَّذ بعد ترقية SQL — يُحمِّل شجرة الحسابات على Production."""
    from odoo.api import Environment
    from odoo import SUPERUSER_ID
    from odoo.addons.rawasi_construction.post_init import load_chart_of_accounts

    env = Environment(cr, SUPERUSER_ID, {})

    if not version:
        _logger.info(
            "RAWASI MIGRATE 19.0.9.7.0: تخطّي — لا نسخة قديمة (تثبيت جديد، post_init_hook كافٍ)"
        )
        return

    _logger.info(
        "RAWASI MIGRATE 19.0.9.7.0: ترقية من %s — تحميل شجرة الحسابات وضبط التسلسلات",
        version,
    )

    # ننفّذ نفس منطق post_init على شركة الـ env الافتراضية
    # ملاحظة: لو فيه عدة شركات يُفضَّل تشغيل هذا يدوياً لكل شركة لاحقاً
    load_chart_of_accounts(env)

    _logger.info("RAWASI MIGRATE 19.0.9.7.0: ✓ مكتمل")
