# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPhaseEApproval(TransactionCase):
    """اختبارات المرحلة E: اعتماد المواد (MAS)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة جدة"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "حديد تسليح", "category": "civil", "standard_cost": 50.0}
        )
        cls.comp = cls.env["rawasi.competition"].create(
            {"title": "مبنى إداري", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": cls.comp.id,
                "reference_item_id": cls.ref.id,
                "description": "توريد حديد تسليح",
                "uom_id": cls.ref.uom_id.id,
                "qty": 10,
                "unit_cost": 50,
                "unit_price": 60,
            }
        )
        cls.comp.action_set_pricing()
        cls.comp.action_submit()
        cls.comp.action_won()
        cls.project = cls.comp.project_id

    def _make(self):
        return self.env["rawasi.material.approval"].create(
            {
                "project_id": self.project.id,
                "boq_item_id": self.boq.id,
                "material_name": "حديد تسليح SABIC",
                "manufacturer": "سابك",
            }
        )

    def test_sequence_assigned(self):
        mas = self._make()
        self.assertTrue(mas.name and mas.name != "جديد")
        self.assertTrue(mas.name.startswith("MAS-"))

    def test_submit_then_approve(self):
        mas = self._make()
        self.assertEqual(mas.state, "draft")
        mas.action_submit()
        self.assertEqual(mas.state, "submitted")
        mas.action_approve()
        self.assertEqual(mas.state, "approved")

    def test_approve_as_noted_and_resubmit_cycle(self):
        mas = self._make()
        mas.action_submit()
        mas.action_request_resubmit()
        self.assertEqual(mas.state, "resubmit")
        mas.action_submit()
        self.assertEqual(mas.state, "submitted")
        mas.action_approve_as_noted()
        self.assertEqual(mas.state, "approved_as_noted")

    def test_reject_then_reset(self):
        mas = self._make()
        mas.action_submit()
        mas.action_reject()
        self.assertEqual(mas.state, "rejected")
        mas.action_reset_to_draft()
        self.assertEqual(mas.state, "draft")

    def test_invalid_transition_raises(self):
        mas = self._make()
        with self.assertRaises(UserError):
            mas.action_approve()

    def test_merge_without_pdf_raises(self):
        mas = self._make()
        with self.assertRaises(UserError):
            mas.action_merge_attachments_pdf()
