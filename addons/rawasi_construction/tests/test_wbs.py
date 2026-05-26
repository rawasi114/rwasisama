# -*- coding: utf-8 -*-
import base64
import os
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

SCHED_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "schedule")


def _b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read())


@tagged("post_install", "-at_install")
class TestWbs(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع اختبار WBS"})

    def test_generate_phases(self):
        self.project.action_generate_wbs_phases()
        mains = self.project.wbs_activity_ids.filtered(
            lambda a: a.phase_id and not a.parent_id
        )
        self.assertEqual(len(mains), 6, "يجب توليد المراحل الرئيسية الست")
        # مهام فرعية مولّدة تحت المراحل
        children = self.project.wbs_activity_ids.filtered(lambda a: a.parent_id)
        self.assertTrue(len(children) >= 6, "يجب توليد مهام فرعية")
        # لا يكرّر المراحل الرئيسية عند الاستدعاء مرة أخرى
        self.project.action_generate_wbs_phases()
        self.assertEqual(
            len(self.project.wbs_activity_ids.filtered(
                lambda a: a.phase_id and not a.parent_id)),
            6,
        )

    def test_duration_and_dates(self):
        act = self.env["rawasi.wbs.activity"].create({
            "project_id": self.project.id,
            "name": "نشاط",
            "date_start": date(2026, 1, 1),
            "date_end": date(2026, 1, 10),
        })
        self.assertEqual(act.duration, 10)

    def test_invalid_dates_raise(self):
        with self.assertRaises(ValidationError):
            self.env["rawasi.wbs.activity"].create({
                "project_id": self.project.id,
                "name": "نشاط خاطئ",
                "date_start": date(2026, 1, 10),
                "date_end": date(2026, 1, 1),
            })

    def test_planned_cost_from_boq(self):
        comp = self.env["rawasi.competition"].create({"name": "م"})
        item = self.env["rawasi.boq.item"].create({
            "competition_id": comp.id, "name": "بند", "quantity": 10, "unit_cost": 50,
        })  # total_cost 500
        act = self.env["rawasi.wbs.activity"].create({
            "project_id": self.project.id, "name": "نشاط مكلّف",
            "boq_item_ids": [(6, 0, item.ids)],
        })
        self.assertAlmostEqual(act.planned_cost, 500.0, places=2)

    def test_schedule_import(self):
        # المراحل لازمة لمطابقة أسماء المراحل
        self.env["rawasi.wbs.phase"].search([])  # seeded
        wizard = self.env["rawasi.schedule.import.wizard"].create({
            "project_id": self.project.id,
            "file": _b64(os.path.join(SCHED_DIR, "schedule_sample.xlsx")),
            "filename": "schedule_sample.xlsx",
        })
        wizard.action_import()
        acts = self.project.wbs_activity_ids
        self.assertEqual(len(acts), 6, "يجب استيراد 6 أنشطة")

        mob = acts.filtered(lambda a: a.name == "تجهيز الموقع")
        self.assertEqual(mob.progress, 100.0)

        milestone = acts.filtered(lambda a: a.name == "التسليم الابتدائي")
        self.assertTrue(milestone.is_milestone, "يجب وسم المعلَم")

    def test_schedule_import_rejects_bad_file(self):
        # ملف BOQ ليس جدولاً زمنياً (لا أعمدة تواريخ) -> رفض
        boq_dir = os.path.join(os.path.dirname(__file__), "fixtures", "etimad")
        wizard = self.env["rawasi.schedule.import.wizard"].create({
            "project_id": self.project.id,
            "file": _b64(os.path.join(boq_dir, "etimad_invalid_not_boq.xlsx")),
            "filename": "invalid.xlsx",
        })
        with self.assertRaises(UserError):
            wizard.action_import()
