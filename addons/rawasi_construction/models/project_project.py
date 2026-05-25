# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    wbs_activity_ids = fields.One2many(
        "rawasi.wbs.activity", "project_id", string="أنشطة WBS"
    )
    wbs_count = fields.Integer(string="عدد الأنشطة", compute="_compute_wbs_count")

    # ملاحظة: نستخدم بادئة rawasi_ لتفادي التعارض مع حقول موديولات أخرى
    # (مثل documents_project الذي يعرّف document_ids/document_count على المشروع).
    rawasi_document_ids = fields.One2many("rawasi.document", "project_id", string="المستندات")
    rawasi_mas_ids = fields.One2many("rawasi.material.approval", "project_id", string="اعتمادات المواد")
    rawasi_dsr_ids = fields.One2many("rawasi.daily.report", "project_id", string="التقارير اليومية")
    rawasi_ncr_ids = fields.One2many("rawasi.ncr", "project_id", string="تقارير عدم المطابقة")
    rawasi_rfi_ids = fields.One2many("rawasi.rfi", "project_id", string="طلبات المعلومات")

    rawasi_document_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_mas_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_dsr_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_ncr_count = fields.Integer(compute="_compute_rawasi_phase4_counts")
    rawasi_rfi_count = fields.Integer(compute="_compute_rawasi_phase4_counts")

    def _compute_wbs_count(self):
        for project in self:
            project.wbs_count = len(project.wbs_activity_ids)

    def _compute_rawasi_phase4_counts(self):
        for project in self:
            project.rawasi_document_count = len(project.rawasi_document_ids)
            project.rawasi_mas_count = len(project.rawasi_mas_ids)
            project.rawasi_dsr_count = len(project.rawasi_dsr_ids)
            project.rawasi_ncr_count = len(project.rawasi_ncr_ids)
            project.rawasi_rfi_count = len(project.rawasi_rfi_ids)

    def _rawasi_open_related(self, name, model):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_documents(self):
        return self._rawasi_open_related(_("المستندات"), "rawasi.document")

    def action_open_mas(self):
        return self._rawasi_open_related(_("اعتمادات المواد"), "rawasi.material.approval")

    def action_open_dsr(self):
        return self._rawasi_open_related(_("التقارير اليومية"), "rawasi.daily.report")

    def action_open_ncr(self):
        return self._rawasi_open_related(_("تقارير عدم المطابقة"), "rawasi.ncr")

    def action_open_rfi(self):
        return self._rawasi_open_related(_("طلبات المعلومات"), "rawasi.rfi")

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
