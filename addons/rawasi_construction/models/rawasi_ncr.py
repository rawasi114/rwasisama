# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiNcr(models.Model):
    _name = "rawasi.ncr"
    _description = "تقرير عدم مطابقة (Non-Conformance Report)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"

    name = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    # رابط اختياري لبند جدول الكميات
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    subject = fields.Char(string="الموضوع", required=True, tracking=True)
    description = fields.Text(string="وصف عدم المطابقة", required=True)
    severity = fields.Selection(
        [("minor", "بسيط"), ("major", "جسيم"), ("critical", "حرج")],
        string="الخطورة",
        default="minor",
        required=True,
        tracking=True,
    )
    raised_by_id = fields.Many2one(
        "res.users", string="رفعه", default=lambda self: self.env.user
    )
    issue_date = fields.Date(
        string="تاريخ الرصد", default=fields.Date.context_today
    )
    root_cause = fields.Text(string="السبب الجذري")
    corrective_action = fields.Text(string="الإجراء التصحيحي")
    responsible_id = fields.Many2one("res.users", string="المسؤول عن المعالجة")
    due_date = fields.Date(string="تاريخ الاستحقاق")
    closed_date = fields.Date(string="تاريخ الإغلاق", readonly=True, copy=False)
    state = fields.Selection(
        [
            ("open", "مفتوح"),
            ("in_progress", "قيد المعالجة"),
            ("closed", "مغلق"),
            ("void", "ملغى"),
        ],
        string="الحالة",
        default="open",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_ncr_attachment_rel",
        "ncr_id",
        "attachment_id",
        string="المرفقات",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.ncr"
                ) or "/"
        return super().create(vals_list)

    def _report_xmlid(self):
        return "rawasi_construction.action_report_ncr"

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_close(self):
        self.write({"state": "closed", "closed_date": fields.Date.context_today(self)})

    def action_void(self):
        self._ensure_admin()
        self.write({"state": "void"})

    def action_reopen(self):
        self._ensure_admin()
        self.write({"state": "open", "closed_date": False})
