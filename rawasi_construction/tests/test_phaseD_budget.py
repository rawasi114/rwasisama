# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPhaseDBudget(TransactionCase):
    """اختبارات المرحلة D: لوحة ميزانية المشروع."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة جدة"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "أسفلت", "category": "civil", "standard_cost": 100.0}
        )
        cls.comp = cls.env["rawasi.competition"].create(
            {"title": "طريق دائري", "partner_id": cls.partner.id}
        )
        cls.env["rawasi.boq.item"].create(
            {
                "competition_id": cls.comp.id,
                "reference_item_id": cls.ref.id,
                "description": "توريد وفرش أسفلت",
                "uom_id": cls.ref.uom_id.id,
                "qty": 100,
                "unit_cost": 100,
                "unit_price": 130,
            }
        )
        cls.comp.action_set_pricing()
        cls.comp.action_submit()
        cls.comp.action_won()
        cls.project = cls.comp.project_id

    def test_estimated_cost_from_boq(self):
        self.assertEqual(self.project.rawasi_budget_estimated_cost, 100 * 100)

    def test_consumption_and_remaining_no_spend(self):
        self.assertEqual(self.project.rawasi_budget_actual_spent, 0.0)
        self.assertEqual(self.project.rawasi_budget_remaining, 10000.0)
        self.assertEqual(self.project.rawasi_budget_consumption_pct, 0.0)
        self.assertFalse(self.project.rawasi_budget_overrun)

    def test_spend_via_analytic_drives_overrun(self):
        if not self.project.account_id:
            self.skipTest("لا يوجد حساب تحليلي على المشروع")
        self.env["account.analytic.line"].create(
            {
                "name": "صرف أسفلت",
                "account_id": self.project.account_id.id,
                "amount": -12000.0,
            }
        )
        self.project.invalidate_recordset()
        self.assertEqual(self.project.rawasi_budget_actual_spent, 12000.0)
        self.assertTrue(self.project.rawasi_budget_overrun)
        self.assertEqual(self.project.rawasi_budget_remaining, 10000.0 - 12000.0)
