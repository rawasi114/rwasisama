# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    wbs_activity_ids = fields.One2many(
        "rawasi.wbs.activity", "project_id", string="أنشطة WBS"
    )
    wbs_count = fields.Integer(string="عدد الأنشطة", compute="_compute_wbs_count")

    def _compute_wbs_count(self):
        for project in self:
            project.wbs_count = len(project.wbs_activity_ids)

    def action_generate_wbs_phases(self):
        """يولّد المراحل الخمس (من القوالب) كأنشطة عليا إن لم تكن موجودة."""
        Activity = self.env["rawasi.wbs.activity"]
        phases = self.env["rawasi.wbs.phase"].search([], order="sequence")
        for project in self:
            existing = project.wbs_activity_ids.filtered(lambda a: a.phase_id and not a.parent_id)
            existing_phase_ids = existing.mapped("phase_id")
            seq = 10
            for phase in phases:
                if phase in existing_phase_ids:
                    continue
                Activity.create({
                    "project_id": project.id,
                    "phase_id": phase.id,
                    "name": phase.name,
                    "sequence": seq,
                })
                seq += 10
        return self.action_open_wbs()

    def action_open_wbs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("هيكل تجزئة العمل (WBS)"),
            "res_model": "rawasi.wbs.activity",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_schedule_import(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("استيراد الجدول الزمني"),
            "res_model": "rawasi.schedule.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }
