# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestAcceptanceScenarios(TransactionCase):
    """سيناريوهات القبول الإلزامية (PART F) — تحقق end-to-end على Odoo فعلي.

    S1 — مقاولات نقي · S3 — التصنيع الداخلي · S4 — تجاوز إداري ·
    S5 — دور عابر للموديولين · S6 — تحليل متعدد الأبعاد.
    (S2 الورشة النقي يُغطّى في rawasi_workshop/tests).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "rawasi_base.require_pin_on_issue", "False"
        )
        cls.partner = cls.env["res.partner"].create({"name": "وزارة التعليم"})

    # ------------------------------------------------------------------
    # S1 — مقاولات نقي (بلا تصنيع داخلي)
    # ------------------------------------------------------------------
    def test_s1_pure_construction_flow(self):
        cement = self.env["rawasi.reference.item"].create(
            {"name": "أسمنت مقاوم", "category": "civil", "procurement_type": "purchase",
             "standard_cost": 14.0}
        )
        comp = self.env["rawasi.competition"].create(
            {"title": "مدرسة الأمل", "partner_id": self.partner.id}
        )
        self.env["rawasi.boq.item"].create(
            {"competition_id": comp.id, "reference_item_id": cement.id,
             "description": "أسمنت", "uom_id": cement.uom_id.id, "qty": 500, "unit_price": 16}
        )
        comp.action_set_pricing(); comp.action_submit(); comp.action_won()
        project = comp.project_id
        self.assertTrue(project.account_id, "للمشروع حساب تحليلي")

        # MR → اعتماد → صرف
        mr = self.env["rawasi.material.request"].create(
            {"project_id": project.id, "boq_item_id": comp.boq_item_ids[0].id}
        )
        self.env["rawasi.material.request.line"].create(
            {"request_id": mr.id, "reference_item_id": cement.id, "description": "أسمنت",
             "qty": 200, "uom_id": cement.uom_id.id, "unit_cost": 14}
        )
        mr.action_approve_supervisor(); mr.action_approve_budget()
        mr.action_forward_purchase(); mr.action_issue()
        self.assertEqual(mr.state, "issued")

        # DSR يستهلك المواد
        dsr = self.env["rawasi.dsr"].create({"project_id": project.id})
        self.env["rawasi.dsr.material"].create(
            {"dsr_id": dsr.id, "product_id": cement.product_id.id, "description": "أسمنت", "qty": 200}
        )
        dsr.action_confirm()

        # IPC → اعتماد → دفع
        ipc = self.env["rawasi.ipc"].create({"project_id": project.id})
        self.env["rawasi.ipc.line"].create(
            {"ipc_id": ipc.id, "boq_item_id": comp.boq_item_ids[0].id,
             "description": "أسمنت", "current_qty": 200, "unit_price": 16}
        )
        ipc.action_submit(); ipc.action_approve(); ipc.action_mark_paid()
        self.assertEqual(ipc.state, "paid")
        self.assertEqual(ipc.amount_work, 3200.0)

        # ضمان حسن تنفيذ
        bg = self.env["rawasi.bank.guarantee"].create(
            {"project_id": project.id, "guarantee_type": "performance", "amount": 100000,
             "expiry_date": date.today() + timedelta(days=200)}
        )
        self.assertEqual(bg.state, "active")

    # ------------------------------------------------------------------
    # S4 — تجاوز إداري يُسجَّل في سجل التدقيق المشترك
    # ------------------------------------------------------------------
    def test_s4_admin_override_audit(self):
        section = self.env.ref("rawasi_workshop.section_carp")
        mo = self.env["rawasi.workshop.mo"].create(
            {"section_id": section.id, "partner_id": self.partner.id}
        )
        audit = self.env["rawasi.audit.trail"].log(
            mo, "override", reason="تجاوز بوابة الدفع باعتماد المالك", detail="حالة طارئة"
        )
        self.assertEqual(audit.event, "override")
        self.assertEqual(audit.model_name, "rawasi.workshop.mo")
        # append-only
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            audit.write({"reason": "x"}); audit.flush_recordset()

    # ------------------------------------------------------------------
    # S5 — محاسب واحد يعمل على المقاولات + الورشة بـ session واحد
    # ------------------------------------------------------------------
    def test_s5_cross_cutting_accountant(self):
        accountant = self.env["res.users"].create(
            {
                "name": "محاسب رواسي",
                "login": "acc_cross_test",
                "groups_id": [(6, 0, [self.env.ref("rawasi_base.group_rawasi_accountant").id])],
            }
        )
        # مشروع + MR مقاولات للاعتماد
        comp = self.env["rawasi.competition"].create(
            {"title": "مشروع S5", "partner_id": self.partner.id}
        )
        comp.action_set_pricing()
        self.env["rawasi.boq.item"].create(
            {"competition_id": comp.id, "description": "بند", "uom_id": self.env.ref("uom.product_uom_unit").id,
             "qty": 1, "unit_price": 100}
        )
        comp.action_submit(); comp.action_won()
        mr = self.env["rawasi.material.request"].create({"project_id": comp.project_id.id})
        mr.action_approve_supervisor()
        # المحاسب يعتمد ميزانية المقاولات
        mr.with_user(accountant).action_approve_budget()
        self.assertEqual(mr.accountant_user_id, accountant)

        # ونفس المحاسب يعتمد طلب مواد ورشة
        section = self.env.ref("rawasi_workshop.section_carp")
        wmo = self.env["rawasi.workshop.mo"].create({"section_id": section.id, "is_internal": True})
        wmr = self.env["rawasi.workshop.material.request"].create(
            {"section_id": section.id, "mo_id": wmo.id}
        )
        wmr.action_approve_supervisor()
        wmr.with_user(accountant).action_approve_budget()
        self.assertEqual(wmr.accountant_user_id, accountant)

    # ------------------------------------------------------------------
    # S6 — التحليل متعدد الأبعاد: خطتان منفصلتان (مشاريع + أقسام)
    # ------------------------------------------------------------------
    def test_s6_multidim_analytic_plans(self):
        plan_root = self.env.ref("rawasi_base.analytic_plan_rawasi")
        plan_proj = self.env.ref("rawasi_base.analytic_plan_construction")
        plan_ws = self.env.ref("rawasi_base.analytic_plan_workshop")
        self.assertEqual(plan_proj.parent_id, plan_root)
        self.assertEqual(plan_ws.parent_id, plan_root)

        # مشروع مقاولات ← حساب تحليلي في خطة المشاريع
        comp = self.env["rawasi.competition"].create(
            {"title": "مشروع تحليلي", "partner_id": self.partner.id}
        )
        comp.action_set_pricing()
        self.env["rawasi.boq.item"].create(
            {"competition_id": comp.id, "description": "بند",
             "uom_id": self.env.ref("uom.product_uom_unit").id, "qty": 1, "unit_price": 1}
        )
        comp.action_submit(); comp.action_won()
        self.assertEqual(comp.project_id.account_id.plan_id, plan_proj)

        # قسم ورشة ← حساب تحليلي في خطة الأقسام
        section = self.env.ref("rawasi_workshop.section_carp")
        self.assertEqual(section.analytic_account_id.plan_id, plan_ws)

        # البُعدان منفصلان (خطتان مختلفتان تحت نفس الجذر) → تحليل مزدوج ممكن
        self.assertNotEqual(comp.project_id.account_id.plan_id, section.analytic_account_id.plan_id)
