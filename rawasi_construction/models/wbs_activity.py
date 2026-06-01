# -*- coding: utf-8 -*-
"""هيكل تجزئة العمل (WBS) والجدول الزمني — نسخة مبسَّطة.

شجرة أنشطة لكل مشروع: الأنشطة العليا تمثّل المراحل، والأبناء يمثّلون المهام.
لكل نشاط تاريخ بداية ونهاية ونسبة إنجاز وأنشطة سابقة (Predecessors) لعرضها على
مخطط Gantt. ربط اختياري ببنود جدول الكميات لاحتساب التكلفة المخططة.

تبسيط مقصود مقارنةً بنسخة الإنتاج: حُذفت آليات المسار الحرج وخط الأساس والطفو
الكلي لأنها كانت تربك المستخدمين ونادراً ما تُحدَّث.
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RawasiWbsActivity(models.Model):
    _name = "rawasi.wbs.activity"
    _description = "نشاط في هيكل تجزئة العمل — رواسي"
    _order = "sequence, date_start, id"
    _parent_store = True

    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('rawasi_is_construction', '=', True)]",
    )
    parent_id = fields.Many2one(
        "rawasi.wbs.activity",
        string="النشاط الأب",
        ondelete="cascade",
        index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "rawasi.wbs.activity", "parent_id", string="الأنشطة الفرعية"
    )

    name = fields.Char(string="النشاط", required=True)
    sequence = fields.Integer(default=10)
    is_milestone = fields.Boolean(string="معلَم (Milestone)")

    date_start = fields.Date(string="تاريخ البداية")
    date_end = fields.Date(string="تاريخ النهاية")
    duration = fields.Integer(
        string="المدة (أيام)", compute="_compute_duration", store=True
    )
    progress = fields.Float(string="نسبة الإنجاز %", default=0.0)

    predecessor_ids = fields.Many2many(
        "rawasi.wbs.activity",
        "rawasi_wbs_activity_dependency_rel",
        "successor_id",
        "predecessor_id",
        string="الأنشطة السابقة",
    )

    # الربط ببنود جدول الكميات — حفاظاً على مبدأ «بند جدول الكميات هو النواة»
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
        for activity in self:
            if (
                activity.date_start
                and activity.date_end
                and activity.date_end >= activity.date_start
            ):
                activity.duration = (activity.date_end - activity.date_start).days + 1
            else:
                activity.duration = 0

    @api.depends("boq_item_ids.total_cost")
    def _compute_planned_cost(self):
        for activity in self:
            activity.planned_cost = sum(activity.boq_item_ids.mapped("total_cost"))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for activity in self:
            if (
                activity.date_start
                and activity.date_end
                and activity.date_end < activity.date_start
            ):
                raise ValidationError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")
