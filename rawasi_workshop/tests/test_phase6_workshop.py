# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestWorkshop(TransactionCase):
    """اختبارات الورشة (المرحلة 6): الأقسام + MO + بوابات الدفع + تكامل البيع."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section = cls.env.ref("rawasi_workshop.section_carp")
        cls.partner = cls.env["res.partner"].create({"name": "عميل ورشة"})
        cls.product = cls.env["product.product"].create(
            {"name": "باب خشبي 90×210", "list_price": 1890.0, "type": "consu"}
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "rawasi_base.require_pin_on_issue", "False"
        )

    def test_sections_loaded(self):
        self.assertTrue(self.section)
        self.assertEqual(self.section.code, "CARP")
        steel = self.env.ref("rawasi_workshop.section_steel")
        self.assertEqual(steel.code, "STEEL")
        # حساب تحليلي ضمن خطة الورشة
        self.assertEqual(
            self.section.analytic_account_id.plan_id,
            self.env.ref("rawasi_base.analytic_plan_workshop"),
        )

    def test_mo_payment_gates_external(self):
        mo = self.env["rawasi.workshop.mo"].create(
            {"section_id": self.section.id, "partner_id": self.partner.id}
        )
        self.assertTrue(mo.name.startswith("WMO-"))
        self.env["rawasi.workshop.mo.line"].create(
            {
                "mo_id": mo.id,
                "product_id": self.product.id,
                "description": "باب",
                "qty": 10,
                "uom_id": self.product.uom_id.id,
                "unit_price": 1890,
            }
        )
        self.assertEqual(mo.amount_total, 18900.0)
        mo.action_confirm()
        # لا دفعة → لا يمكن بدء التصنيع
        self.assertFalse(mo.can_start_production)
        with self.assertRaises(UserError):
            mo.action_start_production()
        # دفعة 50%
        mo.amount_received = 9450.0
        self.assertTrue(mo.can_start_production)
        mo.action_start_production()
        self.assertEqual(mo.state, "in_production")
        mo.action_done()
        # لا يمكن التسليم قبل 100%
        self.assertFalse(mo.can_start_delivery)
        with self.assertRaises(UserError):
            mo.action_deliver()
        mo.amount_received = 18900.0
        self.assertTrue(mo.can_start_delivery)
        mo.action_deliver()
        self.assertEqual(mo.state, "delivered")

    def test_mo_internal_bypasses_gates(self):
        mo = self.env["rawasi.workshop.mo"].create(
            {"section_id": self.section.id, "is_internal": True}
        )
        self.env["rawasi.workshop.mo.line"].create(
            {
                "mo_id": mo.id,
                "product_id": self.product.id,
                "description": "باب داخلي",
                "qty": 12,
                "uom_id": self.product.uom_id.id,
                "unit_price": 1800,
            }
        )
        self.assertTrue(mo.no_payment_required)
        self.assertTrue(mo.can_start_production)
        self.assertTrue(mo.can_start_delivery)
        mo.action_confirm()
        mo.action_start_production()
        mo.action_done()
        mo.action_deliver()
        self.assertEqual(mo.state, "delivered")

    def test_sale_order_creates_mo(self):
        self.product.product_tmpl_id.write(
            {
                "rawasi_produce_in_workshop": True,
                "rawasi_workshop_section_id": self.section.id,
                "sale_ok": True,
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 5})
                ],
            }
        )
        so.action_confirm()
        self.assertEqual(so.workshop_mo_count, 1)
        mo = so.workshop_mo_ids
        self.assertEqual(mo.section_id, self.section)
        self.assertEqual(len(mo.product_line_ids), 1)
        self.assertEqual(mo.product_line_ids.qty, 5)

    def test_workshop_material_request_workflow(self):
        mo = self.env["rawasi.workshop.mo"].create(
            {"section_id": self.section.id, "is_internal": True}
        )
        mr = self.env["rawasi.workshop.material.request"].create(
            {"section_id": self.section.id, "mo_id": mo.id}
        )
        self.assertTrue(mr.name.startswith("WMR-"))
        mr.action_approve_supervisor()
        mr.action_approve_budget()
        mr.action_forward_purchase()
        mr.action_issue()
        self.assertEqual(mr.state, "issued")
        audit = self.env["rawasi.audit.trail"].search(
            [
                ("model_name", "=", "rawasi.workshop.material.request"),
                ("res_id", "=", mr.id),
            ]
        )
        self.assertTrue(audit)

    def test_workshop_notification_templates(self):
        templates = self.env["rawasi.notification.hook"]._get_templates()
        self.assertIn("mo_confirmed", templates)
        self.assertIn("mo_delivered", templates)
