# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudget(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع الميزانية"})
        self.comp = self.env["rawasi.competition"].create({"name": "منافسة الميزانية"})
        # بند ميزانيته 1000 (10 × 100)
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id, "name": "خرسانة",
            "quantity": 10, "unit_cost": 100, "unit_price": 130,
        })

    def _mr(self, qty, cost):
        return self.env["rawasi.material.request"].create({
            "project_id": self.project.id,
            "line_ids": [(0, 0, {
                "boq_item_id": self.item.id, "quantity": qty, "unit_cost": cost,
            })],
        })

    def test_budget_within_limit_approves(self):
        mr = self._mr(5, 100)   # 500 <= 1000
        mr.action_submit()
        mr.action_approve()
        self.assertEqual(mr.state, "approved")
        self.assertAlmostEqual(self.item.amount_committed, 500.0, places=2)
        self.assertAlmostEqual(self.item.amount_remaining, 500.0, places=2)

    def test_over_budget_blocks_without_override(self):
        mr = self._mr(15, 100)  # 1500 > 1000
        mr.action_submit()
        self.assertTrue(mr.has_over_budget)
        with self.assertRaises(UserError):
            mr.action_approve()

    def test_override_allows_approval_and_audits(self):
        mr = self._mr(15, 100)
        mr.action_submit()
        # التجاوز يتطلب صلاحية مدير المشاريع — ننفّذه كمدير (admin لديه دور المدير العام)
        admin = self.env.ref("base.user_admin")
        mr.with_user(admin).action_override_budget()
        self.assertTrue(mr.override_budget)
        mr.action_approve()
        self.assertEqual(mr.state, "approved")
        self.assertGreater(self.item.amount_consumed, self.item.total_cost)
        self.assertEqual(self.item.budget_state, "over")

    def test_locked_item_blocks(self):
        self.item.is_locked = True
        mr = self._mr(1, 100)
        mr.action_submit()
        with self.assertRaises(UserError):
            mr.action_approve()

    def test_mr_to_po_moves_commitment(self):
        mr = self._mr(5, 100)
        mr.action_submit()
        mr.action_approve()
        self.assertAlmostEqual(self.item.amount_committed, 500.0, places=2)
        # إنشاء أمر شراء ينقل الطلب إلى "تم الشراء" (يتوقف عن الاحتساب)
        mr.action_create_po()
        self.assertEqual(mr.state, "procured")
        po = self.env["rawasi.purchase.order"].search([("mr_id", "=", mr.id)])
        self.assertTrue(po)
        # PO مسودة لا تُحتسب بعد
        self.assertAlmostEqual(self.item.amount_committed, 0.0, places=2)
        po.action_confirm()
        # PO مؤكد: الكمية المفتوحة تُحتسب مرتبطاً
        self.assertAlmostEqual(self.item.amount_committed, 500.0, places=2)
        self.assertAlmostEqual(self.item.amount_spent, 0.0, places=2)

    def test_grn_moves_committed_to_spent(self):
        mr = self._mr(5, 100)
        mr.action_submit()
        mr.action_approve()
        mr.action_create_po()
        po = self.env["rawasi.purchase.order"].search([("mr_id", "=", mr.id)])
        po.action_confirm()
        po.action_create_grn()
        grn = self.env["rawasi.goods.receipt"].search([("order_id", "=", po.id)])
        self.assertTrue(grn)
        grn.action_validate()
        # بعد الاستلام: المنفَق 500، المرتبط 0
        self.assertAlmostEqual(self.item.amount_spent, 500.0, places=2)
        self.assertAlmostEqual(self.item.amount_committed, 0.0, places=2)
        self.assertAlmostEqual(self.item.amount_remaining, 500.0, places=2)
        self.assertEqual(po.state, "received")
