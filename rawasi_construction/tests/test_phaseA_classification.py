# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPhaseAClassification(TransactionCase):
    """اختبارات المرحلة A: التصنيفات (LCGPA/SBC) + إثراء البند المرجعي + حقول BOQ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "بلدية الخبر"})
        cls.lcgpa = cls.env["rawasi.lcgpa.code"].create(
            {"code": "2002", "name_ar": "الخرسانة", "category": "الخرسانة"}
        )
        cls.sbc = cls.env["rawasi.sbc.code"].create(
            {"code": "SBC-201", "name": "الخرسانة المسلحة"}
        )

    # ----------------------------------------------------------------- LCGPA
    def test_lcgpa_display_label(self):
        self.assertEqual(self.lcgpa.display_label, "[2002] الخرسانة")

    def test_lcgpa_seed_loaded(self):
        """تأكيد بذر بيانات LCGPA من ملف CSV."""
        seed = self.env.ref("rawasi_construction.lcgpa_2002", raise_if_not_found=False)
        self.assertTrue(seed, "يجب تحميل رموز LCGPA البذرية")
        self.assertEqual(seed.code, "2002")

    @mute_logger("odoo.sql_db")
    def test_lcgpa_code_unique(self):
        with self.assertRaises(Exception):
            self.env["rawasi.lcgpa.code"].create(
                {"code": "2002", "name_ar": "مكرر"}
            )
            self.env.flush_all()

    def test_lcgpa_match_code(self):
        self.assertEqual(self.lcgpa.match_code("2002"), self.lcgpa)
        self.assertFalse(self.lcgpa.match_code("غير محدد"))
        self.assertFalse(self.lcgpa.match_code(""))

    def test_lcgpa_reference_count(self):
        ref = self.env["rawasi.reference.item"].create(
            {"name": "خرسانة C35", "category": "civil", "lcgpa_code_id": self.lcgpa.id}
        )
        self.assertIn(ref, self.lcgpa.reference_item_ids)
        self.assertEqual(self.lcgpa.reference_item_count, 1)

    # ------------------------------------------------------------------- SBC
    def test_sbc_display_label(self):
        self.assertEqual(self.sbc.display_label, "SBC-201 - الخرسانة المسلحة")

    def test_sbc_match_code(self):
        self.assertEqual(self.sbc.match_code("SBC-201"), self.sbc)
        self.assertFalse(self.sbc.match_code("غير محدد"))

    # -------------------------------------------------- إثراء البند المرجعي
    def test_reference_item_classification_links(self):
        ref = self.env["rawasi.reference.item"].create(
            {
                "name": "بلوك أسمنتي",
                "category": "civil",
                "lcgpa_code_id": self.lcgpa.id,
                "sbc_code_id": self.sbc.id,
            }
        )
        self.assertEqual(ref.lcgpa_code_id, self.lcgpa)
        self.assertEqual(ref.sbc_code_id, self.sbc)

    # ------------------------------------------------------- حقول جدول الكميات
    def test_boq_total_cost_and_subtotal(self):
        ref = self.env["rawasi.reference.item"].create(
            {"name": "حديد تسليح", "category": "steel", "standard_cost": 2700.0}
        )
        comp = self.env["rawasi.competition"].create(
            {"title": "جسر", "partner_id": self.partner.id}
        )
        boq = self.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": ref.id,
                "serial": "1",
                "category": "حديد",
                "description": "حديد تسليح 16مم",
                "uom_id": ref.uom_id.id,
                "qty": 5,
                "unit_cost": 2700,
                "unit_price": 3000,
            }
        )
        self.assertEqual(boq.total_cost, 5 * 2700)
        self.assertEqual(boq.subtotal, 5 * 3000)
        self.assertEqual(boq.serial, "1")
        self.assertEqual(boq.category, "حديد")

    def test_boq_onchange_defaults_costs(self):
        ref = self.env["rawasi.reference.item"].create(
            {"name": "رمل", "category": "civil", "standard_cost": 40.0}
        )
        boq = self.env["rawasi.boq.item"].new(
            {"reference_item_id": ref.id}
        )
        boq._onchange_reference_item()
        self.assertEqual(boq.unit_cost, 40.0)
        self.assertEqual(boq.unit_price, 40.0)
        self.assertEqual(boq.description, ref.name)
