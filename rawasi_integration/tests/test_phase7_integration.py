# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestInternalWorkshop(TransactionCase):
    """اختبار السيناريو الذهبي للتصنيع الداخلي (المرحلة 7) — end-to-end."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "بلدية حفر الباطن"})
        # بند مرجعي بمسار تصنيع داخلي (نجارة)
        cls.door = cls.env["rawasi.reference.item"].create(
            {
                "name": "باب خشبي داخلي",
                "category": "carpentry",
                "procurement_type": "in_house_workshop",
                "standard_cost": 1800.0,
            }
        )
        comp = cls.env["rawasi.competition"].create(
            {"title": "فيلا أبو غيث", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": cls.door.id,
                "description": "أبواب خشبية داخلية",
                "uom_id": cls.door.uom_id.id,
                "qty": 12,
                "unit_price": 2200,
            }
        )
        comp.action_set_pricing()
        comp.action_submit()
        comp.action_won()
        cls.project = comp.project_id
        cls.env["ir.config_parameter"].sudo().set_param(
            "rawasi_base.require_pin_on_issue", "False"
        )

    def test_internal_partner_exists(self):
        partner = self.env.ref("rawasi_integration.partner_internal_construction")
        self.assertTrue(partner)

    def test_golden_scenario_end_to_end(self):
        # 1) طلب مواد مقاولات على بند التصنيع الداخلي
        mr = self.env["rawasi.material.request"].create(
            {"project_id": self.project.id, "boq_item_id": self.boq.id}
        )
        self.assertEqual(mr.procurement_type, "in_house_workshop")
        # 2) سلسلة الاعتماد حتى الميزانية
        mr.action_approve_supervisor()
        mr.action_approve_budget()
        # 3) زر التصنيع الداخلي ينشئ أمر تصنيع داخلي
        action = mr.action_internal_workshop_quote()
        iwo = self.env["rawasi.internal.workshop.order"].browse(action["res_id"])
        self.assertTrue(iwo)
        self.assertEqual(iwo.section_id.code, "CARP", "يخمّن قسم النجارة من التصنيف")
        self.assertEqual(iwo.qty, 12)
        self.assertEqual(iwo.cost_estimate, 1800.0 * 12)
        # الهامش 5% افتراضياً
        self.assertEqual(iwo.final_price, 1800.0 * 12 * 1.05)
        # 4) إنشاء أمر البيع الداخلي
        iwo.action_create_sale_order()
        self.assertTrue(iwo.sale_order_id)
        self.assertTrue(iwo.sale_order_id.is_internal_workshop)
        self.assertEqual(iwo.state, "sale_pending")
        # 5) اعتماد (تأكيد) أمر البيع → ينشئ MO داخلي بلا بوابة دفع
        iwo.sale_order_id.action_confirm()
        mo = iwo.workshop_mo_id
        self.assertTrue(mo, "يجب إنشاء أمر تصنيع")
        self.assertTrue(mo.is_internal)
        self.assertTrue(mo.no_payment_required)
        self.assertTrue(mo.can_start_production, "تُتجاوز بوابة الـ 50%")
        self.assertEqual(iwo.state, "in_production")
        # 6) التصنيع حتى الاكتمال
        mo.action_confirm()
        mo.action_start_production()
        mo.action_done()
        # 7) عند الاكتمال: يُقفل طلب مواد المقاولات + يُسلَّم للمشروع
        self.assertEqual(mr.state, "issued", "طلب المقاولات يُقفل تلقائياً")
        self.assertEqual(iwo.state, "delivered_to_project")
        # سجل تدقيق للتسليم
        audit = self.env["rawasi.audit.trail"].search(
            [("model_name", "=", "rawasi.internal.workshop.order"), ("res_id", "=", iwo.id)]
        )
        self.assertTrue(audit)

    def test_quote_requires_budget_approval(self):
        from odoo.exceptions import UserError

        mr = self.env["rawasi.material.request"].create(
            {"project_id": self.project.id, "boq_item_id": self.boq.id}
        )
        # قبل اعتماد الميزانية: ممنوع
        with self.assertRaises(UserError):
            mr.action_internal_workshop_quote()

    def test_margin_zero(self):
        mr = self.env["rawasi.material.request"].create(
            {"project_id": self.project.id, "boq_item_id": self.boq.id}
        )
        mr.action_approve_supervisor()
        mr.action_approve_budget()
        action = mr.action_internal_workshop_quote()
        iwo = self.env["rawasi.internal.workshop.order"].browse(action["res_id"])
        iwo.margin_pct = "0"
        self.assertEqual(iwo.final_price, iwo.cost_estimate)

    def test_dashboard_kpis(self):
        dash = self.env["rawasi.dashboard.unified"].create({})
        # المشروع المُنشأ في setUp يجب أن يُحتسب
        self.assertGreaterEqual(dash.active_projects, 1)
        # لا أخطاء في حساب المؤشرات
        dash.action_refresh()
