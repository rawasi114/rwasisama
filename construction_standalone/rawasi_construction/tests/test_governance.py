# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGovernance(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع الحوكمة"})
        self.comp = self.env["rawasi.competition"].create({"name": "منافسة الحوكمة"})
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id,
            "name": "خرسانة مسلحة",
            "quantity": 10.0,
            "unit_cost": 100.0,
            "unit_price": 120.0,
        })
        # مستخدم غير إداري (مدير مشاريع) لاختبار القيود
        self.pd_user = self.env["res.users"].create({
            "name": "مدير مشاريع",
            "login": "pd_governance",
            "group_ids": [(6, 0, [
                self.env.ref("rawasi_construction.group_projects_director").id,
            ])],
        })

    # ── تقارير PDF لكل النماذج تُصرّف (compile) دون أخطاء QWeb ─────
    def test_all_reports_render(self):
        mr = self.env["rawasi.material.request"].create({
            "project_id": self.project.id,
            "line_ids": [(0, 0, {
                "boq_item_id": self.item.id, "quantity": 1.0, "unit_cost": 10.0,
            })],
        })
        po = self.env["rawasi.purchase.order"].create({
            "project_id": self.project.id,
            "line_ids": [(0, 0, {
                "boq_item_id": self.item.id, "quantity": 1.0, "unit_cost": 10.0,
            })],
        })
        grn = self.env["rawasi.goods.receipt"].create({
            "order_id": po.id,
            "line_ids": [(0, 0, {"po_line_id": po.line_ids[0].id, "quantity": 1.0})],
        })
        doc = self.env["rawasi.document"].create({
            "name": "مخطط", "project_id": self.project.id, "document_type": "drawing",
        })
        dsr = self.env["rawasi.daily.report"].create({
            "project_id": self.project.id,
            "labor_ids": [(0, 0, {"trade": "نجار", "worker_count": 4})],
        })
        ncr = self.env["rawasi.ncr"].create({
            "project_id": self.project.id, "subject": "خلل", "description": "وصف",
        })
        rfi = self.env["rawasi.rfi"].create({
            "project_id": self.project.id, "subject": "استفسار", "question": "سؤال",
        })
        mas = self.env["rawasi.material.approval"].create({
            "project_id": self.project.id, "boq_item_id": self.item.id,
            "material_name": "مادة",
        })
        report_obj = self.env["ir.actions.report"]
        cases = [
            ("rawasi_construction.action_report_competition", self.comp),
            ("rawasi_construction.action_report_material_request", mr),
            ("rawasi_construction.action_report_purchase_order", po),
            ("rawasi_construction.action_report_goods_receipt", grn),
            ("rawasi_construction.action_report_document", doc),
            ("rawasi_construction.action_report_dsr", dsr),
            ("rawasi_construction.action_report_ncr", ncr),
            ("rawasi_construction.action_report_rfi", rfi),
            ("rawasi_construction.action_report_mas_cover", mas),
        ]
        for xmlid, rec in cases:
            with self.subTest(report=xmlid):
                html, dummy = report_obj._render_qweb_html(xmlid, rec.ids)
                self.assertTrue(html)

    # ── حارس الإلغاء/الإرجاع: غير الإداري يُمنع، الإداري يُسمح ────
    def test_reset_blocked_for_non_admin(self):
        self.comp.action_start_pricing()
        self.comp.action_submit()
        with self.assertRaises(UserError):
            self.comp.with_user(self.pd_user).action_reset_to_draft()

    def test_reset_allowed_for_admin(self):
        self.comp.action_start_pricing()
        self.comp.action_submit()
        self.comp.action_reset_to_draft()  # env.user = admin (group_system)
        self.assertEqual(self.comp.state, "draft")

    def test_po_cancel_blocked_for_non_admin(self):
        po = self.env["rawasi.purchase.order"].create({
            "project_id": self.project.id,
            "line_ids": [(0, 0, {
                "boq_item_id": self.item.id, "quantity": 1.0, "unit_cost": 10.0,
            })],
        })
        with self.assertRaises(UserError):
            po.with_user(self.pd_user).action_cancel()

    # ── قيد الحذف: غير الإداري لا يحذف، الإداري يحذف ─────────────
    def test_delete_blocked_for_non_admin(self):
        with self.assertRaises(AccessError):
            self.comp.with_user(self.pd_user).unlink()

    def test_delete_allowed_for_admin(self):
        comp = self.env["rawasi.competition"].create({"name": "للحذف"})
        comp.unlink()
        self.assertFalse(comp.exists())
