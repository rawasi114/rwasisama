# -*- coding: utf-8 -*-
"""Pre-migration 19.0.10.0.0 — إعادة تسمية بنية كتالوج البنود إلى المصطلحات
الاحترافية المعتمدة (reference_item / item_variant / audit_trail).

السكربت يحفظ كل البيانات المخزَّنة (الـ 519 بنداً + المرادفات + سجل التدقيق)
وينقلها إلى المخطط الجديد قبل أن تحاول ملفات الـ data أو الـ ORM تحميل
الموديلات بأسمائها الجديدة.

كل الأوامر idempotent — إن سبق تنفيذها لن تتعطّل.
"""
import logging

_logger = logging.getLogger(__name__)


def _rename_table(cr, old, new):
    cr.execute("""
        SELECT to_regclass(%s), to_regclass(%s)
    """, [old, new])
    old_exists, new_exists = cr.fetchone()
    if old_exists and not new_exists:
        cr.execute("ALTER TABLE %s RENAME TO %s" % (old, new))
        _logger.info("renamed table %s → %s", old, new)


def _rename_column(cr, table, old_col, new_col):
    cr.execute("""
        SELECT to_regclass(%s)
    """, [table])
    if cr.fetchone()[0] is None:
        return
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name IN (%s, %s)
    """, [table, old_col, new_col])
    cols = {r[0] for r in cr.fetchall()}
    if old_col in cols and new_col not in cols:
        cr.execute("ALTER TABLE %s RENAME COLUMN %s TO %s" % (table, old_col, new_col))
        _logger.info("renamed %s.%s → %s.%s", table, old_col, table, new_col)


def migrate(cr, version):
    # ── 1) إعادة تسمية الجداول ──────────────────────────────────
    _rename_table(cr, 'rawasi_item_master',          'rawasi_reference_item')
    _rename_table(cr, 'rawasi_item_synonym',         'rawasi_item_variant')
    _rename_table(cr, 'rawasi_item_attribute',       'rawasi_item_specification')
    _rename_table(cr, 'rawasi_item_mapping_audit',   'rawasi_audit_trail')
    # taxonomy stays the same name

    # ── 2) إعادة تسمية الأعمدة على rawasi_reference_item ────────
    _rename_column(cr, 'rawasi_reference_item', 'canonical_code', 'reference_code')

    # ── 3) إعادة تسمية الأعمدة على rawasi_item_variant ─────────
    _rename_column(cr, 'rawasi_item_variant', 'canonical_item_id', 'reference_item_id')
    _rename_column(cr, 'rawasi_item_variant', 'text_raw',          'original_text')
    _rename_column(cr, 'rawasi_item_variant', 'text_normalized',   'normalized_text')

    # ── 4) إعادة تسمية الأعمدة على rawasi_item_specification ───
    _rename_column(cr, 'rawasi_item_specification', 'canonical_item_id', 'reference_item_id')

    # ── 5) إعادة تسمية الأعمدة على rawasi_audit_trail ──────────
    _rename_column(cr, 'rawasi_audit_trail', 'canonical_item_id', 'reference_item_id')

    # ── 6) تحديث ir_model: تغيير اسم الموديل ───────────────────
    model_map = [
        ('rawasi.item.master',        'rawasi.reference.item'),
        ('rawasi.item.synonym',       'rawasi.item.variant'),
        ('rawasi.item.attribute',     'rawasi.item.specification'),
        ('rawasi.item.mapping.audit', 'rawasi.audit.trail'),
    ]
    for old, new in model_map:
        cr.execute("UPDATE ir_model SET model=%s WHERE model=%s", [new, old])
        cr.execute("UPDATE ir_model_fields SET model=%s WHERE model=%s", [new, old])
        cr.execute(
            "UPDATE ir_attachment SET res_model=%s WHERE res_model=%s",
            [new, old],
        )

    # ── 7) تحديث ir_model_fields لأسماء الأعمدة الجديدة ────────
    field_map = [
        ('rawasi.reference.item',       'canonical_code',     'reference_code'),
        ('rawasi.item.variant',         'canonical_item_id',  'reference_item_id'),
        ('rawasi.item.variant',         'text_raw',           'original_text'),
        ('rawasi.item.variant',         'text_normalized',    'normalized_text'),
        ('rawasi.item.specification',   'canonical_item_id',  'reference_item_id'),
        ('rawasi.audit.trail',          'canonical_item_id',  'reference_item_id'),
    ]
    for model, old_name, new_name in field_map:
        cr.execute(
            "UPDATE ir_model_fields SET name=%s WHERE model=%s AND name=%s",
            [new_name, model, old_name],
        )

    # ── 8) ir_model_data: تحديث model للسجلات اللي تشير للنماذج المعاد تسميتها
    for old, new in model_map:
        cr.execute(
            "UPDATE ir_model_data SET model=%s WHERE model=%s",
            [new, old],
        )

    # ── 9) تنظيف XML IDs القديمة من حقول related أو computed لو وجدت ──
    # (الـ ORM سيعيد بناء أي compute/related تلقائياً عند load_modules)

    _logger.info("rawasi_construction: catalog rename completed successfully")
