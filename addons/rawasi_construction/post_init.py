# -*- coding: utf-8 -*-
"""تهيئة محاسبة رواسي بعد تثبيت الموديول.

التسلسل:
1) تحميل قالب أودو الافتراضي ``generic_coa`` (للحصول على الدفاتر + الضرائب
   + إعدادات الشركة الأساسية مثل bank/cash/suspense accounts).
2) إضافة شجرة حسابات رواسي الـ٢٧٢ حساباً فوقه (موزّعة على ٧ مجموعات).
3) ضبط تسلسلات طلبات البيع والشراء لتبدأ من ١٠٠٠١ بدل ١ (لمصداقية أول معاملة).

ترقيم فواتير العملاء والدفعات يبدأ تلقائياً من ١٠٠٠١ عبر تعديل
``_get_starting_sequence`` في ``models/account_move.py`` — لا حاجة لخطوة هنا.
"""

import csv
import logging
import os

_logger = logging.getLogger(__name__)


def load_chart_of_accounts(env):
    """نقطة الدخول الموحَّدة لـ ``_rawasi_post_init_hook``."""
    company = env.company
    _ensure_generic_coa(env, company)
    _create_rawasi_accounts(env, company)
    _bump_business_sequences(env)


def _ensure_generic_coa(env, company):
    """يستدعي قالب ``generic_coa`` فوراً للحصول على الدفاتر + الضرائب.

    يُلغي ``_auto_install_template`` بعدها لأن `_register_hook` يستدعيه
    أيضاً، فنحن نسبقه ونمنع التكرار.
    """
    if company.chart_template:
        _logger.info(
            "RAWASI: chart_template مضبوط مسبقاً (%s) — تخطّي generic_coa",
            company.chart_template,
        )
    else:
        _logger.info("RAWASI: تحميل generic_coa للحصول على الدفاتر والضرائب")
        env["account.chart.template"].try_loading(
            "generic_coa", company=company, install_demo=False
        )
    # نمنع _register_hook من تكرار العملية
    if hasattr(env.registry, "_auto_install_template"):
        del env.registry._auto_install_template


def _create_rawasi_accounts(env, company):
    """يقرأ CSV الحسابات ويُنشئ السجلات الـ٢٧٢ في الشركة."""
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "rawasi_chart_of_accounts.csv"
    )
    if not os.path.isfile(csv_path):
        _logger.warning("RAWASI: لم يُعثر على %s", csv_path)
        return

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

            # نتفادى التضارب مع الحسابات الافتراضية لو وُجد بنفس الكود
            if Account.search_count([("code", "=", code)]):
                _logger.debug("RAWASI: كود %s موجود سلفاً في القالب الافتراضي", code)
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
        "RAWASI: شجرة الحسابات — أُنشئ %d / تخطّى %d (إجمالي %d)",
        created, skipped, created + skipped,
    )


def _bump_business_sequences(env):
    """يضبط بدايات تسلسل sale.order / purchase.order على ١٠٠٠١.

    نلمس فقط التسلسلات التي لم تُستهلَك (number_next_actual ≤ ١) لتفادي
    قفز سيء التوقيت في عمليات قائمة.
    """
    seq_codes = ["sale.order", "purchase.order", "sale.order.template"]
    Sequence = env["ir.sequence"]
    bumped = []
    for code in seq_codes:
        for seq in Sequence.search([("code", "=", code)]):
            if seq.number_next_actual <= 1:
                seq.number_next_actual = 10001
                bumped.append(f"{code}({seq.id})")
    if bumped:
        _logger.info("RAWASI: تسلسلات بدأت من ١٠٠٠١ — %s", ", ".join(bumped))
    else:
        _logger.info("RAWASI: لا تسلسلات إضافية تحتاج ضبط (مسبوقة بالفعل)")
