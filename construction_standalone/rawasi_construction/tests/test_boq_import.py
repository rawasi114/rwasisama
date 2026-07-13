# -*- coding: utf-8 -*-
import base64
import os

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

FIX_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "etimad")


def _fixture_b64(name):
    with open(os.path.join(FIX_DIR, name), "rb") as fh:
        return base64.b64encode(fh.read())


@tagged("post_install", "-at_install")
class TestBoqImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.competition = self.env["rawasi.competition"].create(
            {"name": "منافسة اختبار الاستيراد"}
        )

    def _import(self, filename, replace=False):
        wizard = self.env["rawasi.boq.import.wizard"].create(
            {
                "competition_id": self.competition.id,
                "file": _fixture_b64(filename),
                "filename": filename,
                "replace_existing": replace,
            }
        )
        return wizard.action_import()

    def _item(self, serial):
        return self.competition.boq_item_ids.filtered(lambda i: i.serial == str(serial))

    # ── Variant A: 10 أعمدة، الكمية في العمود E، الفئة فارغة ──────
    def test_variant_a_import(self):
        self._import("etimad_boq_sample_variant_a.xlsx")
        items = self.competition.boq_item_ids
        self.assertEqual(len(items), 39, "يجب استيراد 39 بنداً من Variant A")

        first = self._item(1)
        self.assertEqual(first.unit_id.code, "sqm", "م² يجب أن تُطبَّع إلى متر مربع")
        self.assertAlmostEqual(first.quantity, 9.75, places=2)
        self.assertFalse(first.category, "الفئة فارغة في Variant A")
        self.assertTrue(first.name)

        # تطبيع متر طولي: السلسلة 5 وحدتها "م.ط"
        self.assertEqual(self._item(5).unit_id.code, "lm")

    # ── Variant B: 9 أعمدة، الكمية أخيرة، Forward-Fill + رموز SBC ──
    def test_variant_b_import_and_forward_fill(self):
        self._import("etimad_boq_sample_variant_b.xlsx")
        items = self.competition.boq_item_ids
        self.assertEqual(len(items), 209, "يجب استيراد 209 بنود من Variant B")

        # صف مرساة (excel row 9 = serial 8): الفئة "الخرسانة" والرمز 2002
        anchor = self._item(8)
        self.assertEqual(anchor.category, "الخرسانة")
        self.assertEqual(anchor.sbc_code_id.code, "2002")

        # Forward-Fill: serial 9 (لا مرساة) يرث "الخرسانة"
        self.assertEqual(self._item(9).category, "الخرسانة")

        # "غير محدد" لا يُربط برمز SBC
        first = self._item(1)
        self.assertEqual(first.category, "الأعمال الأولية والموقع العام")
        self.assertFalse(first.sbc_code_id)

        # حالة حافة: وصف طويل (1100+ حرف) للسلسلة 100
        self.assertGreater(len(self._item(100).name), 1000)

    # ── رفض ملف ليس جدول كميات ─────────────────────────────────
    def test_reject_invalid_file(self):
        with self.assertRaises(UserError):
            self._import("etimad_invalid_not_boq.xlsx")

    # ── الاستبدال ───────────────────────────────────────────────
    def test_replace_existing(self):
        self._import("etimad_boq_sample_variant_a.xlsx")
        self.assertEqual(len(self.competition.boq_item_ids), 39)
        self._import("etimad_boq_sample_variant_a.xlsx", replace=True)
        self.assertEqual(len(self.competition.boq_item_ids), 39, "الاستبدال لا يضاعف البنود")

    # ── الاستيراد ينقل الحالة إلى التسعير ──────────────────────
    def test_import_moves_to_pricing(self):
        self.assertEqual(self.competition.state, "draft")
        self._import("etimad_boq_sample_variant_a.xlsx")
        self.assertEqual(self.competition.state, "pricing")
