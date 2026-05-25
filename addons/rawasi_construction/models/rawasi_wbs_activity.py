# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiWbsActivity(models.Model):
    _name = "rawasi.wbs.activity"
    _description = "نشاط/مرحلة في هيكل تجزئة العمل (WBS)"
    _order = "sequence, date_start, id"
    _parent_store = True

    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True,
        ondelete="cascade", index=True,
    )
    phase_id = fields.Many2one("rawasi.wbs.phase", string="المرحلة")
    parent_id = fields.Many2one(
        "rawasi.wbs.activity", string="النشاط الأب",
        ondelete="cascade", index=True,
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("rawasi.wbs.activity", "parent_id", string="الأنشطة الفرعية")

    name = fields.Char(string="النشاط", required=True)
    sequence = fields.Integer(default=10)
    is_milestone = fields.Boolean(string="معلَم (Milestone)")

    # الجدول الزمني المخطط
    date_start = fields.Date(string="تاريخ البداية")
    date_end = fields.Date(string="تاريخ النهاية")
    duration = fields.Integer(string="المدة (أيام)", compute="_compute_duration", store=True)

    # خط الأساس (Baseline) والفعلي (Actual) — لمقارنة الأداء في Gantt
    baseline_start = fields.Date(string="بداية خط الأساس")
    baseline_end = fields.Date(string="نهاية خط الأساس")
    actual_start = fields.Date(string="البداية الفعلية")
    actual_end = fields.Date(string="النهاية الفعلية")

    progress = fields.Float(string="نسبة الإنجاز %", default=0.0)

    predecessor_ids = fields.Many2many(
        "rawasi.wbs.activity",
        "rawasi_wbs_activity_dependency_rel",
        "successor_id",
        "predecessor_id",
        string="الأنشطة السابقة (Predecessors)",
    )

    # الربط ببنود جدول الكميات — يحافظ على مبدأ «بند BOQ هو النواة»
    boq_item_ids = fields.Many2many(
        "rawasi.boq.item",
        "rawasi_wbs_activity_boq_rel",
        "activity_id",
        "boq_item_id",
        string="بنود جدول الكميات",
    )

    company_id = fields.Many2one(related="project_id.company_id", store=True)
    currency_id = fields.Many2one(related="project_id.company_id.currency_id")
    planned_cost = fields.Monetary(
        string="التكلفة المخططة", compute="_compute_planned_cost", store=True
    )

    @api.depends("date_start", "date_end")
    def _compute_duration(self):
        for act in self:
            if act.date_start and act.date_end and act.date_end >= act.date_start:
                act.duration = (act.date_end - act.date_start).days + 1
            else:
                act.duration = 0

    @api.depends("boq_item_ids.total_cost")
    def _compute_planned_cost(self):
        for act in self:
            act.planned_cost = sum(act.boq_item_ids.mapped("total_cost"))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        from odoo.exceptions import ValidationError
        for act in self:
            if act.date_start and act.date_end and act.date_end < act.date_start:
                raise ValidationError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")
