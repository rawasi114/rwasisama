# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestConstructionCore(TransactionCase):
    """اختبارات نواة المقاولات (المرحلة 4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "بلدية حفر الباطن"})
        cls.ref_item = cls.env["rawasi.reference.item"].create(
            {
                "name": "خرسانة جاهزة C35",
                "category": "civil",
                "procurement_type": "purchase",
                "standard_cost": 250.0,
            }
        )

    def test_reference_item_creates_product(self):
        self.assertTrue(self.ref_item.product_id, "يجب إنشاء منتج تلقائياً للبند المرجعي")
        self.assertEqual(self.ref_item.product_id.default_code, self.ref_item.code)
        self.assertEqual(
            self.ref_item.product_id.rawasi_reference_item_id, self.ref_item
        )

    def test_reference_item_sequence(self):
        self.assertTrue(self.ref_item.code.startswith("REF-"))

    def test_reference_item_sync_on_write(self):
        self.ref_item.standard_cost = 300.0
        self.assertEqual(self.ref_item.product_id.standard_price, 300.0)

    def test_competition_lifecycle_and_project(self):
        comp = self.env["rawasi.competition"].create(
            {"title": "فيلا أبو غيث", "partner_id": self.partner.id}
        )
        self.assertTrue(comp.name.startswith("COMP-"))
        self.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": self.ref_item.id,
                "description": "خرسانة",
                "uom_id": self.ref_item.uom_id.id,
                "qty": 10,
                "unit_price": 300,
            }
        )
        self.assertEqual(comp.amount_total, 3000.0)
        self.assertEqual(comp.boq_count, 1)
        # لا يمكن التقديم قبل التسعير
        with self.assertRaises(UserError):
            comp.action_submit()
        comp.action_set_pricing()
        comp.action_submit()
        comp.action_won()
        self.assertEqual(comp.state, "won")
        self.assertTrue(comp.project_id, "يجب إنشاء مشروع عند الفوز")
        self.assertTrue(comp.project_id.rawasi_is_construction)
        self.assertEqual(comp.project_id.rawasi_competition_id, comp)

    def test_submit_requires_boq(self):
        comp = self.env["rawasi.competition"].create(
            {"title": "بلا بنود", "partner_id": self.partner.id}
        )
        comp.action_set_pricing()
        with self.assertRaises(UserError):
            comp.action_submit()

    def test_boq_procurement_type_related(self):
        ws_item = self.env["rawasi.reference.item"].create(
            {
                "name": "باب خشبي جاهز",
                "category": "carpentry",
                "procurement_type": "in_house_workshop",
                "standard_cost": 1800.0,
            }
        )
        comp = self.env["rawasi.competition"].create(
            {"title": "مدرسة", "partner_id": self.partner.id}
        )
        boq = self.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": ws_item.id,
                "description": "أبواب",
                "uom_id": ws_item.uom_id.id,
                "qty": 12,
                "unit_price": 1890,
            }
        )
        self.assertEqual(boq.procurement_type, "in_house_workshop")
        self.assertEqual(boq.subtotal, 12 * 1890)

    def test_bom(self):
        cement = self.env["rawasi.reference.item"].create(
            {"name": "أسمنت", "category": "civil", "standard_cost": 15.0}
        )
        bom = self.env["rawasi.bom"].create(
            {"name": "BoM خرسانة", "reference_item_id": self.ref_item.id}
        )
        self.env["rawasi.bom.line"].create(
            {"bom_id": bom.id, "component_item_id": cement.id, "qty": 7}
        )
        self.assertEqual(bom.total_cost, 105.0)
