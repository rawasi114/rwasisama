# -*- coding: utf-8 -*-
import base64
import io

from odoo.tests.common import TransactionCase, tagged

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


def _xlsx(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue())


@tagged("post_install", "-at_install")
class TestPricedImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.comp = self.env["rawasi.competition"].create({"name": "منافسة استيراد مُسعّر"})

    def _import(self, headers, rows):
        wiz = self.env["rawasi.boq.import.wizard"].create({
            "competition_id": self.comp.id,
            "file": _xlsx(headers, rows),
            "filename": "boq.xlsx",
        })
        wiz.action_import()

    def test_import_unit_price(self):
        self._import(
            ["وصف البند", "الكمية", "الوحدة", "سعر الوحدة"],
            [["خرسانة مسلحة", 10, "م3", 150], ["حديد تسليح", 5, "طن", 2000]],
        )
        items = self.comp.boq_item_ids
        self.assertEqual(len(items), 2)
        khorsana = items.filtered(lambda i: "خرسانة" in i.name)
        self.assertEqual(khorsana.unit_price, 150.0)
        self.assertEqual(khorsana.total_price, 1500.0)
        self.assertEqual(self.comp.amount_total_price, 11500.0)

    def test_import_derives_unit_price_from_total(self):
        # ملف فيه إجمالي السعر فقط (دون سعر الوحدة) -> يُشتقّ سعر الوحدة
        self._import(
            ["وصف البند", "الكمية", "إجمالي السعر"],
            [["دهان", 20, 1000]],
        )
        item = self.comp.boq_item_ids
        self.assertEqual(item.unit_price, 50.0)  # 1000 / 20
        self.assertEqual(item.total_price, 1000.0)
