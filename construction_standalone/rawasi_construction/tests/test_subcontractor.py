# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSubcontractor(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع باطن"})
        self.comp = self.env["rawasi.competition"].create({
            "name": "منافسة", "project_id": self.project.id,
        })
        self.project.rawasi_competition_id = self.comp.id
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id, "name": "تركيب بلاط",
            "quantity": 100.0, "unit_cost": 80.0, "unit_price": 100.0,
        })
        self.sub = self.env["rawasi.subcontractor"].create({
            "name": "مقاول البلاط",
            "specialization": "تركيبات",
        })

    # ── تسلسلات ──────────────────────────────────────────────────
    def test_sequences(self):
        self.assertTrue(self.sub.code.startswith("SUB/"))
        contract = self.env["rawasi.subcontract"].create({
            "subcontractor_id": self.sub.id, "project_id": self.project.id,
        })
        self.assertTrue(contract.name.startswith("SUB-CON/"))
        ipc = self.env["rawasi.subcontract.ipc"].create({
            "subcontract_id": contract.id,
        })
        self.assertTrue(ipc.name.startswith("SUB-IPC/"))

    # ── احتساب قيمة العقد + المستخلص ─────────────────────────────
    def test_amounts_and_overrun(self):
        contract = self.env["rawasi.subcontract"].create({
            "subcontractor_id": self.sub.id,
            "project_id": self.project.id,
            "retention_percent": 10.0,
            "line_ids": [(0, 0, {
                "boq_item_id": self.item.id,
                "description": "تركيب بلاط",
                "quantity": 50.0, "unit_price": 60.0,
            })],
        })
        self.assertEqual(contract.total_amount, 3000.0)  # 50 × 60
        contract.action_activate()
        self.assertEqual(contract.state, "active")

        ipc = self.env["rawasi.subcontract.ipc"].create({
            "subcontract_id": contract.id, "vat_rate": 15.0,
        })
        ipc.action_generate_lines()
        ln = ipc.line_ids
        self.assertEqual(len(ln), 1)
        ln.period_quantity = 20.0
        # period_value = 20 × 60 = 1200
        # retention 10% = 120 ; net = 1080 ; vat 15% = 162 ; payable = 1242
        self.assertEqual(ipc.subtotal, 1200.0)
        self.assertEqual(ipc.retention_amount, 120.0)
        self.assertEqual(ipc.net_before_vat, 1080.0)
        self.assertEqual(ipc.vat_amount, 162.0)
        self.assertEqual(ipc.net_payable, 1242.0)

        # لا يجوز تجاوز الكمية التعاقدية في بند المستخلص
        with self.assertRaises(ValidationError):
            ln.period_quantity = 999.0

    # ── عزل بالمشروع لمهندس الموقع ──────────────────────────────
    def test_site_engineer_project_isolation(self):
        # مشروع آخر يخص مهندساً غير المختبَر
        other_project = self.env["project.project"].create({"name": "مشروع آخر"})
        # مهندس موقع معيّن على المشروع الأول فقط
        site_eng = self.env["res.users"].create({
            "name": "مهندس موقع",
            "login": "site_sub_test",
            "group_ids": [(6, 0, [
                self.env.ref("rawasi_construction.group_site_engineer").id,
            ])],
        })
        self.project.site_engineer_ids = [(6, 0, [site_eng.id])]

        sub_a = self.env["rawasi.subcontract"].create({
            "subcontractor_id": self.sub.id,
            "project_id": self.project.id,
        })
        sub_b = self.env["rawasi.subcontract"].create({
            "subcontractor_id": self.sub.id,
            "project_id": other_project.id,
        })
        # كأدمن: يرى الاثنين
        all_seen = self.env["rawasi.subcontract"].search([
            ("id", "in", (sub_a + sub_b).ids),
        ])
        self.assertEqual(len(all_seen), 2)
        # كمهندس الموقع: يرى عقد مشروعه فقط (sub_a) لا sub_b
        seen_by_engineer = self.env["rawasi.subcontract"].with_user(site_eng).search([
            ("id", "in", (sub_a + sub_b).ids),
        ])
        self.assertIn(sub_a, seen_by_engineer)
        self.assertNotIn(sub_b, seen_by_engineer)
