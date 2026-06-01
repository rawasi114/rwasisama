# -*- coding: utf-8 -*-
import base64
import io

from odoo.tests.common import TransactionCase


class TestPhaseCImport(TransactionCase):
    """اختبارات المرحلة C: استيراد Excel + محرك المطابقة + المراجعة + التدقيق."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "وزارة التعليم"})
        cls.competition = cls.env["rawasi.competition"].create(
            {"title": "مدرسة 24 فصل", "partner_id": cls.partner.id}
        )
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.ref_concrete = cls.env["rawasi.reference.item"].create(
            {"name": "خرسانة مسلحة C35", "category": "civil", "standard_cost": 250.0}
        )

    def _make_xlsx(self, rows):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        return base64.b64encode(buf.getvalue())

    def _batch_with_rows(self, data_rows):
        header = [
            "الرقم التسلسلي", "الفئة", "الوصف", "المواصفات", "الكمية",
            "وحدة القياس", "التكلفة الإفرادي", "إجمالي التكلفة للبند",
            "السعر الإفرادي", "إجمالي البند",
        ]
        rows = [header] + data_rows
        return self.env["rawasi.import.batch"].create(
            {
                "filename": "boq.xlsx",
                "file_data": self._make_xlsx(rows),
                "competition_id": self.competition.id,
            }
        )

    def test_parse_detects_columns_and_lines(self):
        batch = self._batch_with_rows(
            [
                ["1", "civil", "خرسانة مسلحة C35", "C35", "100", "عدد", "250", "25000", "300", "30000"],
                ["2", "civil", "حديد تسليح 16مم", "B500", "50", "عدد", "2700", "135000", "3000", "150000"],
            ]
        )
        batch.action_parse()
        self.assertEqual(batch.state, "reviewing")
        self.assertEqual(batch.total_lines, 2)
        line1 = batch.line_ids.filtered(lambda l: l.line_number == 1)
        self.assertEqual(line1.original_qty, 100)
        self.assertEqual(line1.original_unit_price, 300)
        self.assertEqual(line1.original_category, "civil")

    def test_exact_text_match(self):
        batch = self._batch_with_rows(
            [["1", "", "خرسانة مسلحة C35", "", "10", "عدد", "250", "2500", "300", "3000"]]
        )
        batch.action_parse()
        line = batch.line_ids
        self.assertEqual(line.suggested_match_id, self.ref_concrete)
        self.assertEqual(line.suggestion_source, "exact_text")
        self.assertGreaterEqual(line.suggestion_confidence, 90.0)

    def test_no_auto_approval_stays_pending(self):
        batch = self._batch_with_rows(
            [["1", "", "خرسانة مسلحة C35", "", "10", "عدد", "250", "2500", "300", "3000"]]
        )
        batch.action_parse()
        self.assertEqual(batch.line_ids.review_status, "pending",
                         "المطابقة لا تعتمد تلقائياً — تبقى بانتظار المراجعة")

    def test_approve_creates_boq_and_learns_variant(self):
        batch = self._batch_with_rows(
            [["1", "", "صب خرسانة مسلحة درجة C35", "", "10", "عدد", "250", "2500", "300", "3000"]]
        )
        batch.action_parse()
        line = batch.line_ids
        line.write({"final_match_id": self.ref_concrete.id, "review_status": "accepted"})
        batch.action_approve()
        self.assertEqual(batch.state, "approved")
        boq = self.competition.boq_item_ids
        self.assertEqual(len(boq), 1)
        self.assertEqual(boq.reference_item_id, self.ref_concrete)
        self.assertEqual(boq.qty, 10)
        # تعلَّم الصياغة البديلة
        variant = self.env["rawasi.item.variant"].search(
            [("reference_item_id", "=", self.ref_concrete.id)]
        )
        self.assertTrue(variant)
        # سجل التدقيق
        audit = self.env["rawasi.import.audit"].search(
            [("import_batch_id", "=", batch.id)]
        )
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.user_action, "accepted")

    def test_variant_enables_future_exact_match(self):
        self.env["rawasi.item.variant"].learn(
            self.ref_concrete, "خرسانه مسلحه عالية المقاومة"
        )
        batch = self._batch_with_rows(
            [["1", "", "خرسانة مسلحة عالية المقاومة", "", "10", "عدد", "0", "0", "0", "0"]]
        )
        batch.action_parse()
        self.assertEqual(batch.line_ids.suggested_match_id, self.ref_concrete)
        self.assertEqual(batch.line_ids.suggestion_source, "exact_text")

    def test_rejected_line_no_boq(self):
        batch = self._batch_with_rows(
            [["1", "", "بند غير معروف تماماً xyz", "", "5", "عدد", "0", "0", "100", "500"]]
        )
        batch.action_parse()
        batch.line_ids.action_reject()
        batch.action_approve()
        self.assertFalse(self.competition.boq_item_ids)
        audit = self.env["rawasi.import.audit"].search([("import_batch_id", "=", batch.id)])
        self.assertEqual(audit.user_action, "rejected")

    def test_pending_no_match_saved_as_boq(self):
        batch = self._batch_with_rows(
            [["1", "", "بند فريد بلا مطابقة zzz", "", "5", "عدد", "10", "50", "100", "500"]]
        )
        batch.action_parse()
        # نتركه pending بلا ترشيح
        batch.action_approve()
        self.assertEqual(len(self.competition.boq_item_ids), 1)
        self.assertFalse(self.competition.boq_item_ids.reference_item_id)
        audit = self.env["rawasi.import.audit"].search([("import_batch_id", "=", batch.id)])
        self.assertEqual(audit.user_action, "saved_no_match")
