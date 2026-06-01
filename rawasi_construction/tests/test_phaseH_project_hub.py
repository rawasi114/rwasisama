# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPhaseHProjectHub(TransactionCase):
    """اختبارات المرحلة H: العرض الموحَّد للمشروع (الأزرار الذكية)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة الرياض"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "بلاط", "category": "civil", "standard_cost": 30.0}
        )
        cls.comp = cls.env["rawasi.competition"].create(
            {"title": "مدرسة", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": cls.comp.id,
                "reference_item_id": cls.ref.id,
                "description": "توريد وتركيب بلاط",
                "uom_id": cls.ref.uom_id.id,
                "qty": 200,
                "unit_cost": 30,
                "unit_price": 40,
            }
        )
        cls.comp.action_set_pricing()
        cls.comp.action_submit()
        cls.comp.action_won()
        cls.project = cls.comp.project_id

    def test_counts_start_zero(self):
        self.assertEqual(self.project.rawasi_material_approval_count, 0)
        self.assertEqual(self.project.rawasi_vo_count, 0)
        self.assertEqual(self.project.rawasi_subcontract_count, 0)

    def test_counts_reflect_related_records(self):
        self.env["rawasi.material.approval"].create(
            {
                "project_id": self.project.id,
                "boq_item_id": self.boq.id,
                "material_name": "بلاط بورسلان",
            }
        )
        self.env["rawasi.variation.order"].create(
            {"project_id": self.project.id, "description": "زيادة كمية", "amount": 500}
        )
        self.project.invalidate_recordset()
        self.assertEqual(self.project.rawasi_material_approval_count, 1)
        self.assertEqual(self.project.rawasi_vo_count, 1)

    def test_action_returns_filtered_domain(self):
        action = self.project.action_rawasi_material_approvals()
        self.assertEqual(action["res_model"], "rawasi.material.approval")
        self.assertIn(("project_id", "=", self.project.id), action["domain"])
        self.assertEqual(
            action["context"]["default_project_id"], self.project.id
        )
