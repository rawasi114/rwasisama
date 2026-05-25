# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPricing(TransactionCase):
    def setUp(self):
        super().setUp()
        self.comp = self.env["rawasi.competition"].create(
            {"name": "منافسة اختبار التسعير", "default_margin_pct": 20.0}
        )

    def _add_item(self, qty, cost, price, name="بند"):
        return self.env["rawasi.boq.item"].create(
            {
                "competition_id": self.comp.id,
                "name": name,
                "quantity": qty,
                "unit_cost": cost,
                "unit_price": price,
            }
        )

    def test_item_and_competition_totals(self):
        self._add_item(10, 100, 130)   # cost 1000, price 1300
        self._add_item(5, 200, 250)    # cost 1000, price 1250
        self.assertAlmostEqual(self.comp.amount_direct_cost, 2000.0, places=2)
        self.assertAlmostEqual(self.comp.amount_total_price, 2550.0, places=2)
        self.assertAlmostEqual(self.comp.margin_amount, 550.0, places=2)

    def test_indirect_percentage_and_total_cost(self):
        self._add_item(10, 100, 130)   # direct 1000
        self.env["rawasi.indirect.cost"].create(
            {
                "competition_id": self.comp.id,
                "name": "إدارة الموقع",
                "compute_type": "percentage",
                "value": 10.0,
            }
        )
        self.assertAlmostEqual(self.comp.amount_indirect_cost, 100.0, places=2)
        self.assertAlmostEqual(self.comp.amount_total_cost, 1100.0, places=2)

    def test_indirect_fixed(self):
        self._add_item(1, 0, 0)
        self.env["rawasi.indirect.cost"].create(
            {
                "competition_id": self.comp.id,
                "name": "تأمين",
                "compute_type": "fixed",
                "value": 5000.0,
            }
        )
        self.assertAlmostEqual(self.comp.amount_indirect_cost, 5000.0, places=2)

    def test_apply_default_margin(self):
        item = self._add_item(10, 100, 0)
        self.comp.action_apply_margin()
        self.assertAlmostEqual(item.unit_price, 120.0, places=2)  # 100 * 1.20

    def test_submit_requires_items(self):
        with self.assertRaises(UserError):
            self.comp.action_submit()

    def test_convert_to_project_requires_won(self):
        self._add_item(1, 100, 130)
        with self.assertRaises(UserError):
            self.comp.action_convert_to_project()
        self.comp.state = "won"
        self.comp.action_convert_to_project()
        self.assertTrue(self.comp.project_id)
        self.assertEqual(self.comp.project_id.name, self.comp.name)
