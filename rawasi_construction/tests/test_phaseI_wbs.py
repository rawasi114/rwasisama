# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPhaseIWbs(TransactionCase):
    """اختبارات المرحلة I: الجدول الزمني وهيكل تجزئة العمل (WBS)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة مكة"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "حفر", "category": "civil", "standard_cost": 10.0}
        )
        cls.comp = cls.env["rawasi.competition"].create(
            {"title": "سد", "partner_id": cls.partner.id}
        )
        cls.boq = cls.env["rawasi.boq.item"].create(
            {
                "competition_id": cls.comp.id,
                "reference_item_id": cls.ref.id,
                "description": "أعمال حفر",
                "uom_id": cls.ref.uom_id.id,
                "qty": 1000,
                "unit_cost": 10,
                "unit_price": 15,
            }
        )
        cls.comp.action_set_pricing()
        cls.comp.action_submit()
        cls.comp.action_won()
        cls.project = cls.comp.project_id

    def test_duration_computed_inclusive(self):
        act = self.env["rawasi.wbs.activity"].create(
            {
                "project_id": self.project.id,
                "name": "مرحلة الحفر",
                "date_start": date(2026, 1, 1),
                "date_end": date(2026, 1, 10),
            }
        )
        self.assertEqual(act.duration, 10)

    def test_end_before_start_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["rawasi.wbs.activity"].create(
                {
                    "project_id": self.project.id,
                    "name": "خطأ",
                    "date_start": date(2026, 1, 10),
                    "date_end": date(2026, 1, 1),
                }
            )

    def test_planned_cost_from_boq(self):
        act = self.env["rawasi.wbs.activity"].create(
            {
                "project_id": self.project.id,
                "name": "حفر",
                "boq_item_ids": [(6, 0, [self.boq.id])],
            }
        )
        self.assertEqual(act.planned_cost, 1000 * 10)

    def test_hierarchy_and_predecessors(self):
        phase = self.env["rawasi.wbs.activity"].create(
            {"project_id": self.project.id, "name": "المرحلة الأولى"}
        )
        task_a = self.env["rawasi.wbs.activity"].create(
            {"project_id": self.project.id, "name": "نشاط أ", "parent_id": phase.id}
        )
        task_b = self.env["rawasi.wbs.activity"].create(
            {
                "project_id": self.project.id,
                "name": "نشاط ب",
                "parent_id": phase.id,
                "predecessor_ids": [(6, 0, [task_a.id])],
            }
        )
        self.assertIn(task_a, phase.child_ids)
        self.assertIn(task_b, phase.child_ids)
        self.assertIn(task_a, task_b.predecessor_ids)

    def test_project_wbs_count(self):
        self.env["rawasi.wbs.activity"].create(
            {"project_id": self.project.id, "name": "نشاط"}
        )
        self.project.invalidate_recordset()
        self.assertEqual(self.project.rawasi_wbs_count, 1)
