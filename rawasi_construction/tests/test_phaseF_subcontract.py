# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestPhaseFSubcontract(TransactionCase):
    """اختبارات المرحلة F: مقاولو الباطن، العقود الفرعية، المستخلصات."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة جدة"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "خرسانة", "category": "civil", "standard_cost": 200.0}
        )
        cls.comp = cls.env["rawasi.competition"].create(
            {"title": "جسر", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": cls.comp.id,
                "reference_item_id": cls.ref.id,
                "description": "صب خرسانة مسلحة",
                "uom_id": cls.ref.uom_id.id,
                "qty": 500,
                "unit_cost": 200,
                "unit_price": 250,
            }
        )
        cls.comp.action_set_pricing()
        cls.comp.action_submit()
        cls.comp.action_won()
        cls.project = cls.comp.project_id
        cls.sub = cls.env["rawasi.subcontractor"].create(
            {"name": "مؤسسة البناء", "specialization": "أعمال خرسانية"}
        )
        cls.contract = cls.env["rawasi.subcontract"].create(
            {
                "subcontractor_id": cls.sub.id,
                "project_id": cls.project.id,
                "retention_percent": 10.0,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "boq_item_id": cls.boq.id,
                            "description": "صب خرسانة",
                            "quantity": 100,
                            "unit_price": 220,
                        },
                    )
                ],
            }
        )

    def test_subcontractor_code_sequence(self):
        self.assertTrue(self.sub.code and self.sub.code != "جديد")
        self.assertTrue(self.sub.code.startswith("SC-"))

    def test_contract_amount_computed(self):
        self.assertEqual(self.contract.contract_amount, 100 * 220)

    def test_activate_requires_lines(self):
        empty = self.env["rawasi.subcontract"].create(
            {"subcontractor_id": self.sub.id, "project_id": self.project.id}
        )
        with self.assertRaises(UserError):
            empty.action_activate()

    def test_activate_and_close(self):
        self.contract.action_activate()
        self.assertEqual(self.contract.state, "active")
        self.contract.action_close()
        self.assertEqual(self.contract.state, "closed")

    def test_ipc_amounts_retention_and_vat(self):
        self.contract.action_activate()
        ipc = self.env["rawasi.subcontract.ipc"].create(
            {"subcontract_id": self.contract.id}
        )
        ipc.action_generate_lines()
        self.assertEqual(len(ipc.line_ids), 1)
        ipc.line_ids.period_quantity = 40
        ipc.invalidate_recordset()
        # قيمة الفترة = 40 × 220 = 8800
        self.assertEqual(ipc.subtotal, 8800.0)
        # المحتجز 10% = 880
        self.assertEqual(ipc.retention_amount, 880.0)
        # الصافي قبل الضريبة = 8800 - 880 = 7920
        self.assertEqual(ipc.net_before_vat, 7920.0)
        # الضريبة 15% = 1188
        self.assertAlmostEqual(ipc.vat_amount, 1188.0, places=2)
        # الصافي المستحق = 7920 + 1188 = 9108
        self.assertAlmostEqual(ipc.net_payable, 9108.0, places=2)

    def test_ipc_overrun_blocked(self):
        self.contract.action_activate()
        ipc = self.env["rawasi.subcontract.ipc"].create(
            {"subcontract_id": self.contract.id}
        )
        ipc.action_generate_lines()
        with self.assertRaises(ValidationError):
            ipc.line_ids.period_quantity = 150  # > 100 contracted

    def test_ipc_approve_and_pay_and_cumulative(self):
        self.contract.action_activate()
        ipc1 = self.env["rawasi.subcontract.ipc"].create(
            {"subcontract_id": self.contract.id}
        )
        ipc1.action_generate_lines()
        ipc1.line_ids.period_quantity = 60
        ipc1.action_approve()
        self.assertEqual(ipc1.state, "approved")
        ipc1.action_mark_paid()
        self.assertEqual(ipc1.state, "paid")
        # المستخلص الثاني يرى 60 كمية سابقة
        ipc2 = self.env["rawasi.subcontract.ipc"].create(
            {"subcontract_id": self.contract.id}
        )
        ipc2.action_generate_lines()
        ipc2.line_ids.invalidate_recordset()
        self.assertEqual(ipc2.line_ids.previous_quantity, 60)
        # محاولة تجاوز التراكمي (60 + 50 = 110 > 100) تُرفض
        with self.assertRaises(ValidationError):
            ipc2.line_ids.period_quantity = 50
