# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestConstructionOperations(TransactionCase):
    """اختبارات عمليات المقاولات (المرحلة 5): MR, DSR, VO, IPC, BG."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "وزارة الإسكان"})
        cls.item = cls.env["rawasi.reference.item"].create(
            {"name": "حديد تسليح", "category": "civil", "standard_cost": 2800.0}
        )
        comp = cls.env["rawasi.competition"].create(
            {"title": "مشروع اختبار", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": cls.item.id,
                "description": "حديد",
                "uom_id": cls.item.uom_id.id,
                "qty": 100,
                "unit_price": 3000,
            }
        )
        comp.action_set_pricing()
        comp.action_submit()
        comp.action_won()
        cls.project = comp.project_id
        # تعطيل PIN لتبسيط اختبار الصرف
        cls.env["ir.config_parameter"].sudo().set_param(
            "rawasi_base.require_pin_on_issue", "False"
        )

    def test_material_request_workflow(self):
        mr = self.env["rawasi.material.request"].create(
            {"project_id": self.project.id, "boq_item_id": self.boq.id}
        )
        self.assertTrue(mr.name.startswith("MR-"))
        self.assertEqual(mr.procurement_type, "purchase")
        self.env["rawasi.material.request.line"].create(
            {
                "request_id": mr.id,
                "reference_item_id": self.item.id,
                "description": "حديد",
                "qty": 50,
                "uom_id": self.item.uom_id.id,
                "unit_cost": 2800,
            }
        )
        self.assertEqual(mr.amount_estimate, 140000.0)
        mr.action_approve_supervisor()
        self.assertEqual(mr.state, "approved_supervisor")
        self.assertTrue(mr.supervisor_user_id)
        mr.action_approve_budget()
        mr.action_forward_purchase()
        mr.action_issue()
        self.assertEqual(mr.state, "issued")
        self.assertTrue(mr.issue_date)
        # سجل تدقيق يُنشأ عند الصرف
        audit = self.env["rawasi.audit.trail"].search(
            [("model_name", "=", "rawasi.material.request"), ("res_id", "=", mr.id)]
        )
        self.assertTrue(audit)

    def test_mr_cannot_skip_states(self):
        mr = self.env["rawasi.material.request"].create({"project_id": self.project.id})
        with self.assertRaises(UserError):
            mr.action_issue()  # لا يمكن الصرف من مسودة

    def test_mr_delete_guard(self):
        mr = self.env["rawasi.material.request"].create({"project_id": self.project.id})
        mr.action_approve_supervisor()
        with self.assertRaises(UserError):
            mr.unlink()  # ممنوع بعد بدء الاعتماد

    def test_dsr(self):
        dsr = self.env["rawasi.dsr"].create({"project_id": self.project.id})
        self.assertTrue(dsr.name.startswith("DSR-"))
        self.env["rawasi.dsr.manpower"].create(
            {"dsr_id": dsr.id, "trade": "حداد", "quantity": 5}
        )
        self.env["rawasi.dsr.manpower"].create(
            {"dsr_id": dsr.id, "trade": "نجار", "quantity": 3}
        )
        self.assertEqual(dsr.total_manpower, 8)
        dsr.action_confirm()
        self.assertEqual(dsr.state, "confirmed")

    def test_variation_order(self):
        vo = self.env["rawasi.variation.order"].create(
            {
                "project_id": self.project.id,
                "vo_type": "omission",
                "description": "حذف بند",
                "amount": 5000,
            }
        )
        self.assertEqual(vo.signed_amount, -5000)
        vo.action_submit()
        vo.action_approve()
        self.assertEqual(vo.state, "approved")

    def test_ipc_calculation(self):
        ipc = self.env["rawasi.ipc"].create(
            {"project_id": self.project.id, "retention_pct": 5.0, "previous_amount": 10000}
        )
        self.env["rawasi.ipc.line"].create(
            {
                "ipc_id": ipc.id,
                "boq_item_id": self.boq.id,
                "description": "حديد",
                "current_qty": 50,
                "unit_price": 3000,
            }
        )
        self.assertEqual(ipc.amount_work, 150000.0)
        self.assertEqual(ipc.retention_amount, 7500.0)
        # net = 150000 - 7500 - 0 - 10000 = 132500
        self.assertEqual(ipc.net_amount, 132500.0)
        ipc.action_submit()
        ipc.action_approve()
        ipc.action_mark_paid()
        self.assertEqual(ipc.state, "paid")

    def test_bank_guarantee(self):
        from datetime import date, timedelta

        bg = self.env["rawasi.bank.guarantee"].create(
            {
                "project_id": self.project.id,
                "guarantee_type": "performance",
                "amount": 50000,
                "expiry_date": date.today() + timedelta(days=20),
            }
        )
        self.assertTrue(bg.name.startswith("BG-"))
        self.assertLessEqual(bg.days_to_expiry, 20)
        # cron لا يفشل ويحدّث الإشعار
        self.env["rawasi.bank.guarantee"]._cron_check_expiry()

    def test_notification_templates_extended(self):
        templates = self.env["rawasi.notification.hook"]._get_templates()
        self.assertIn("mr_issued", templates)
        self.assertIn("guarantee_expiring", templates)
