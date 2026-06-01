# -*- coding: utf-8 -*-
"""ترحيل قبل الترقية إلى الإصدار 19.0.9.0.0 — تحويل النواة الذرية إلى المنتج.

السياسة المعتمدة (بناءً على قرار المالك): بدء نظيف لبيانات بنود جداول الكميات.
- نحذف كل بنود BoQ (rawasi.boq.item) الموجودة، لأن النموذج الجديد سيربطها بمنتج.
- نحذف السطور التابعة (طلبات المواد/أوامر الشراء/المستخلصات) المرتبطة بالبنود المحذوفة.
- نُبقي بقية البيانات: المنافسات، المشاريع، الموردين، رموز SBC، الوحدات.

ملاحظة: الحذف يجري على مستوى قاعدة البيانات (cr.execute) لتجنّب hooks المعقّدة.
"""


_TABLES_DEPENDING_ON_BOQ = [
    # (table, fk_column) — تُمسح أو تُفصل قبل حذف rawasi_boq_item
    ("rawasi_material_request_line", "boq_item_id", "delete"),
    ("rawasi_purchase_order_line", "boq_item_id", "delete"),
    ("rawasi_subcontract_line", "boq_item_id", "delete"),
    ("rawasi_subcontract_ipc_line", "boq_item_id", "delete"),
    ("rawasi_payment_certificate_line", "boq_item_id", "delete"),
    ("rawasi_variation_order_line", "boq_item_id", "delete"),
    ("rawasi_wbs_activity", "boq_item_id", "null"),
    ("rawasi_material_approval", "boq_item_id", "null"),
    ("rawasi_ncr", "boq_item_id", "null"),
    ("rawasi_rfi", "boq_item_id", "null"),
    ("rawasi_document", "boq_item_id", "null"),
    ("rawasi_price_intelligence", "boq_item_id", "null"),
]


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
        (table,),
    )
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return

    # 1) تنظيف الجداول التابعة
    for table, fk, action in _TABLES_DEPENDING_ON_BOQ:
        if not _table_exists(cr, table) or not _column_exists(cr, table, fk):
            continue
        if action == "delete":
            cr.execute(f"DELETE FROM {table} WHERE {fk} IS NOT NULL")
        elif action == "null":
            cr.execute(f"UPDATE {table} SET {fk} = NULL WHERE {fk} IS NOT NULL")

    # 2) حذف بنود جداول الكميات
    if _table_exists(cr, "rawasi_boq_item"):
        cr.execute("DELETE FROM rawasi_boq_item")

    # 3) حذف مراجع ir.model.data المتعلقة بسجلات بنود قديمة (إن وُجدت)
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'rawasi.boq.item'
        """
    )
