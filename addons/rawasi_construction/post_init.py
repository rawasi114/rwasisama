# -*- coding: utf-8 -*-
"""تحميل شجرة حسابات رواسي بعد تثبيت الموديول.

يُستدعى من `_rawasi_post_init_hook` المعرّف في __init__.py.
يُحمّل ٢٧٢ حساباً موزّعة على ٧ مجموعات:
    ١- الأصول       ٢- الالتزامات    ٣- حقوق الملكية   ٤- الإيرادات
    ٥- المخصصات    ٦- تكاليف المشاريع المباشرة          ٧- المصروفات الإدارية
"""

import csv
import logging
import os

_logger = logging.getLogger(__name__)


def load_chart_of_accounts(env):
    """يقرأ CSV الحسابات ويُنشئ السجلات في الشركة الافتراضية.

    يضبط `res_company.chart_template = 'rawasi_coa'` مباشرةً عبر SQL لمنع
    أودو من تشغيل auto-install لـ generic_coa بعد انتهاء التحميل (راجع
    account/models/ir_module.py سطر 67-83).
    """
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "rawasi_chart_of_accounts.csv"
    )
    if not os.path.isfile(csv_path):
        _logger.warning("RAWASI: لم يُعثر على %s", csv_path)
        return

    # امنع auto-install لـ generic_coa: نتجاوز validator حقل Selection
    # بكتابة العمود مباشرة في PostgreSQL.
    company = env.company
    env.cr.execute(
        "UPDATE res_company SET chart_template = %s WHERE id = %s",
        ("rawasi_coa", company.id),
    )
    env.registry.clear_cache()

    # امنع callback المؤجَّل من تشغيل _auto_install_template
    if hasattr(env.registry, "_auto_install_template"):
        del env.registry._auto_install_template

    Account = env["account.account"].with_company(company)
    IrModelData = env["ir.model.data"]
    created, skipped = 0, 0

    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = row["code"].strip()
            xml_name = f"rawasi_coa_{code}"

            if IrModelData.search_count([
                ("module", "=", "rawasi_construction"),
                ("name", "=", xml_name),
            ]):
                skipped += 1
                continue

            account = Account.create({
                "code": code,
                "name": row["name"].strip(),
                "account_type": row["account_type"].strip(),
                "reconcile": row["reconcile"].strip().lower() == "true",
                "company_ids": [(4, company.id)],
            })
            IrModelData.create({
                "module": "rawasi_construction",
                "name": xml_name,
                "model": "account.account",
                "res_id": account.id,
                "noupdate": True,
            })
            created += 1

    _logger.info(
        "RAWASI: تحميل شجرة الحسابات — أُنشئ %d / تخطّى %d", created, skipped
    )
