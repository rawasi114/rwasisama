# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    rawasi_is_construction = fields.Boolean(string="مشروع مقاولات", default=False)
    rawasi_competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المصدر", readonly=True, copy=False
    )
    rawasi_code = fields.Char(string="رمز المشروع", copy=False)
    rawasi_contract_value = fields.Monetary(
        string="قيمة العقد", currency_field="rawasi_currency_id"
    )
    rawasi_currency_id = fields.Many2one(
        "res.currency",
        string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )
    rawasi_date_start = fields.Date(string="تاريخ البدء")
    rawasi_date_end = fields.Date(string="تاريخ الانتهاء التعاقدي")
    rawasi_main_location_id = fields.Many2one(
        "stock.location", string="المخزن الرئيسي للمشروع"
    )
    rawasi_boq_item_ids = fields.One2many(
        "rawasi.boq.item",
        related="rawasi_competition_id.boq_item_ids",
        string="جدول الكميات",
    )

    # ------------------------------------------------------------------
    # لوحة الميزانية
    # ------------------------------------------------------------------
    rawasi_budget_estimated_cost = fields.Monetary(
        compute="_compute_rawasi_budget", string="التكلفة المقدّرة (BOQ)",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_committed = fields.Monetary(
        compute="_compute_rawasi_budget", string="الملتزَم",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_actual_spent = fields.Monetary(
        compute="_compute_rawasi_budget", string="المصروف الفعلي",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_remaining = fields.Monetary(
        compute="_compute_rawasi_budget", string="المتبقّي من المقدّر",
        currency_field="rawasi_currency_id",
    )
    rawasi_budget_consumption_pct = fields.Float(
        compute="_compute_rawasi_budget", string="نسبة الاستهلاك %"
    )
    rawasi_budget_overrun = fields.Boolean(
        compute="_compute_rawasi_budget", string="تجاوز الميزانية"
    )

    # ------------------------------------------------------------------
    # العرض الموحَّد لمهندس الموقع — أزرار ذكية بعدد السجلات المرتبطة
    # ------------------------------------------------------------------
    rawasi_material_request_count = fields.Integer(
        compute="_compute_rawasi_counts", string="طلبات المواد"
    )
    rawasi_material_approval_count = fields.Integer(
        compute="_compute_rawasi_counts", string="اعتمادات المواد"
    )
    rawasi_dsr_count = fields.Integer(
        compute="_compute_rawasi_counts", string="التقارير اليومية"
    )
    rawasi_vo_count = fields.Integer(
        compute="_compute_rawasi_counts", string="أوامر التغيير"
    )
    rawasi_ipc_count = fields.Integer(
        compute="_compute_rawasi_counts", string="المستخلصات"
    )
    rawasi_subcontract_count = fields.Integer(
        compute="_compute_rawasi_counts", string="العقود الفرعية"
    )
    rawasi_wbs_count = fields.Integer(
        compute="_compute_rawasi_counts", string="أنشطة الجدول الزمني"
    )

    def _compute_rawasi_counts(self):
        for project in self:
            domain = [("project_id", "=", project.id)]
            project.rawasi_material_request_count = self.env[
                "rawasi.material.request"
            ].search_count(domain)
            project.rawasi_material_approval_count = self.env[
                "rawasi.material.approval"
            ].search_count(domain)
            project.rawasi_dsr_count = self.env["rawasi.dsr"].search_count(domain)
            project.rawasi_vo_count = self.env[
                "rawasi.variation.order"
            ].search_count(domain)
            project.rawasi_ipc_count = self.env["rawasi.ipc"].search_count(domain)
            project.rawasi_subcontract_count = (
                self.env["rawasi.subcontract"].search_count(domain)
                if "rawasi.subcontract" in self.env
                else 0
            )
            project.rawasi_wbs_count = self.env[
                "rawasi.wbs.activity"
            ].search_count(domain)

    def _action_rawasi_related(self, model, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_rawasi_material_requests(self):
        return self._action_rawasi_related("rawasi.material.request", "طلبات المواد")

    def action_rawasi_material_approvals(self):
        return self._action_rawasi_related(
            "rawasi.material.approval", "اعتمادات المواد"
        )

    def action_rawasi_dsrs(self):
        return self._action_rawasi_related("rawasi.dsr", "التقارير اليومية")

    def action_rawasi_vos(self):
        return self._action_rawasi_related("rawasi.variation.order", "أوامر التغيير")

    def action_rawasi_ipcs(self):
        return self._action_rawasi_related("rawasi.ipc", "المستخلصات الدورية")

    def action_rawasi_subcontracts(self):
        return self._action_rawasi_related("rawasi.subcontract", "العقود الفرعية")

    def action_rawasi_wbs(self):
        action = self._action_rawasi_related(
            "rawasi.wbs.activity", "الجدول الزمني"
        )
        action["view_mode"] = "list,gantt,form"
        return action

    def _compute_rawasi_budget(self):
        AnalyticLine = self.env["account.analytic.line"]
        has_subcontract = "rawasi.subcontract" in self.env
        for project in self:
            estimated = sum(project.rawasi_boq_item_ids.mapped("total_cost"))
            committed = 0.0
            requests = self.env["rawasi.material.request"].search(
                [("project_id", "=", project.id), ("state", "not in", ("draft", "cancelled"))]
            )
            committed += sum(requests.mapped("amount_estimate"))
            if has_subcontract:
                subs = self.env["rawasi.subcontract"].search(
                    [("project_id", "=", project.id), ("state", "not in", ("draft", "cancelled"))]
                )
                committed += sum(subs.mapped("contract_amount"))
            spent = 0.0
            if project.account_id:
                lines = AnalyticLine.search([("account_id", "=", project.account_id.id)])
                spent = -sum(l.amount for l in lines if l.amount < 0)
            project.rawasi_budget_estimated_cost = estimated
            project.rawasi_budget_committed = committed
            project.rawasi_budget_actual_spent = spent
            project.rawasi_budget_remaining = estimated - spent
            project.rawasi_budget_consumption_pct = (
                (spent / estimated * 100.0) if estimated else 0.0
            )
            project.rawasi_budget_overrun = bool(estimated) and spent > estimated
