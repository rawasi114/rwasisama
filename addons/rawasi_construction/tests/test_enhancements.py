# -*- coding: utf-8 -*-
import base64
import io
from datetime import date

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


@tagged("post_install", "-at_install")
class TestScheduleTemplate(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع الجدول"})
        self.Wizard = self.env["rawasi.schedule.import.wizard"]

    def test_template_is_valid_xlsx(self):
        data = self.Wizard._generate_schedule_template()
        self.assertTrue(data[:2] == b"PK")  # ملف xlsx صالح
        wb = openpyxl.load_workbook(io.BytesIO(data))
        self.assertIn("الجدول الزمني", wb.sheetnames)
        self.assertIn("المراحل المتاحة", wb.sheetnames)

    def test_download_template_action(self):
        action = self.Wizard.action_download_template()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn("/web/content/", action["url"])

    def test_import_all_schedule_fields(self):
        headers = [
            "النشاط", "المرحلة", "التسلسل", "تاريخ البداية", "تاريخ النهاية",
            "بداية خط الأساس", "نهاية خط الأساس", "البداية الفعلية",
            "النهاية الفعلية", "نسبة الإنجاز", "معلم",
        ]
        row = [
            "حفر وردم", "الأعمال الإنشائية", 20,
            "2026-02-01", "2026-02-10",
            "2026-02-01", "2026-02-10",
            "2026-02-02", "2026-02-11",
            "50", "لا",
        ]
        wiz = self.Wizard.create({
            "project_id": self.project.id,
            "file": _xlsx(headers, [row]),
            "filename": "sched.xlsx",
        })
        wiz.action_import()
        act = self.project.wbs_activity_ids
        self.assertEqual(len(act), 1)
        self.assertEqual(act.sequence, 20)
        self.assertEqual(act.date_start, date(2026, 2, 1))
        self.assertEqual(act.date_end, date(2026, 2, 10))
        self.assertEqual(act.baseline_start, date(2026, 2, 1))
        self.assertEqual(act.actual_start, date(2026, 2, 2))
        self.assertEqual(act.actual_end, date(2026, 2, 11))
        self.assertEqual(act.progress, 50.0)
        self.assertFalse(act.is_milestone)
