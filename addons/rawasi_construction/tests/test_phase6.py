# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPhase6(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع م6"})
        self.comp = self.env["rawasi.competition"].create({
            "name": "منافسة م6", "project_id": self.project.id,
        })
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id,
            "name": "خرسانة مسلحة",
            "quantity": 10.0,
            "unit_cost": 80.0,
            "unit_price": 100.0,
        })

    # ── أوامر التغيير ───────────────────────────────────────────
    def test_vo_add_qty_applies_to_boq(self):
        vo = self.env["rawasi.variation.order"].create({
            "project_id": self.project.id,
            "subject": "زيادة خرسانة",
            "vo_type": "addition",
            "line_ids": [(0, 0, {
                "change_type": "add_qty", "boq_item_id": self.item.id,
                "quantity": 5.0, "unit_price": 100.0,
            })],
        })
        self.assertTrue(vo.name.startswith("VO/"))
        self.assertEqual(vo.amount_total, 500.0)
        vo.action_submit()
        vo.action_approve()
        self.assertEqual(self.item.quantity, 15.0)
        self.assertTrue(vo.applied)

    def test_vo_omit_qty(self):
        vo = self.env["rawasi.variation.order"].create({
            "project_id": self.project.id, "subject": "حذف", "vo_type": "omission",
            "line_ids": [(0, 0, {
                "change_type": "omit_qty", "boq_item_id": self.item.id,
                "quantity": 3.0, "unit_price": 100.0,
            })],
        })
        self.assertEqual(vo.amount_total, -300.0)
        vo.action_submit()
        vo.action_approve()
        self.assertEqual(self.item.quantity, 7.0)

    def test_vo_new_item_creates_boq(self):
        vo = self.env["rawasi.variation.order"].create({
            "project_id": self.project.id, "subject": "بند جديد", "vo_type": "addition",
            "line_ids": [(0, 0, {
                "change_type": "new_item", "description": "عزل حراري إضافي",
                "quantity": 2.0, "unit_cost": 50.0, "unit_price": 70.0,
            })],
        })
        vo.action_submit()
        vo.action_approve()
        new = self.env["rawasi.boq.item"].search([
            ("competition_id", "=", self.comp.id),
            ("name", "=", "عزل حراري إضافي"),
        ])
        self.assertEqual(len(new), 1)
        self.assertEqual(new.quantity, 2.0)

    # ── المستخلصات ──────────────────────────────────────────────
    def test_pc_generate_and_amounts(self):
        pc = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id, "sequence_no": 1,
            "retention_pct": 10.0, "vat_rate": 15.0,
        })
        pc.action_generate_lines()
        self.assertEqual(len(pc.line_ids), 1)
        line = pc.line_ids
        self.assertEqual(line.contract_qty, 10.0)
        line.work_qty = 4.0
        self.assertEqual(line.amount_work, 400.0)
        self.assertEqual(pc.amount_work_period, 400.0)
        self.assertEqual(pc.retention_amount, 40.0)
        self.assertEqual(pc.amount_net, 360.0)
        self.assertEqual(pc.amount_tax, 54.0)
        self.assertEqual(pc.amount_total, 414.0)

    def test_pc_overrun_blocked(self):
        pc = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id,
        })
        pc.action_generate_lines()
        with self.assertRaises(UserError):
            pc.line_ids.work_qty = 99.0  # يتجاوز الكمية التعاقدية 10

    def test_pc_prev_qty_from_approved(self):
        pc1 = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id, "sequence_no": 1,
        })
        pc1.action_generate_lines()
        pc1.line_ids.work_qty = 4.0
        pc1.action_submit()
        pc1.action_approve()
        pc2 = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id, "sequence_no": 2,
        })
        pc2.action_generate_lines()
        self.assertEqual(pc2.line_ids.prev_qty, 4.0)

    # ── الضمانات البنكية ────────────────────────────────────────
    def _bg(self, days):
        return self.env["rawasi.bank.guarantee"].create({
            "guarantee_type": "performance",
            "expiry_date": fields.Date.today() + timedelta(days=days),
        })

    def test_bg_expiry_states(self):
        self.assertTrue(self._bg(60).name.startswith("BG/"))
        self.assertEqual(self._bg(60).expiry_state, "valid")
        self.assertEqual(self._bg(10).expiry_state, "soon")
        self.assertEqual(self._bg(-5).expiry_state, "expired")

    def test_bg_cron_marks_expired(self):
        bg = self._bg(-1)
        self.assertEqual(bg.state, "active")
        self.env["rawasi.bank.guarantee"]._cron_check_expiry()
        self.assertEqual(bg.state, "expired")

    # ── تصيير تقارير المرحلة السادسة (يكشف أخطاء QWeb) ──────────
    def test_phase6_reports_render(self):
        vo = self.env["rawasi.variation.order"].create({
            "project_id": self.project.id, "subject": "تغيير", "vo_type": "addition",
            "line_ids": [(0, 0, {
                "change_type": "add_qty", "boq_item_id": self.item.id,
                "quantity": 1.0, "unit_price": 100.0,
            })],
        })
        pc = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id,
        })
        pc.action_generate_lines()
        bg = self._bg(30)
        report_obj = self.env["ir.actions.report"]
        cases = [
            ("rawasi_construction.action_report_variation_order", vo),
            ("rawasi_construction.action_report_payment_certificate", pc),
            ("rawasi_construction.action_report_bank_guarantee", bg),
        ]
        for xmlid, rec in cases:
            with self.subTest(report=xmlid):
                html, dummy = report_obj._render_qweb_html(xmlid, rec.ids)
                self.assertTrue(html)
