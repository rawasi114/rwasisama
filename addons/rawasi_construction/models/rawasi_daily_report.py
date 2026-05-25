# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiDailyReport(models.Model):
    _name = "rawasi.daily.report"
    _description = "التقرير اليومي للموقع (Daily Site Report)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "report_date desc, id desc"

    name = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    report_date = fields.Date(
        string="التاريخ", default=fields.Date.context_today, required=True, tracking=True
    )
    prepared_by_id = fields.Many2one(
        "res.users", string="أعدّه", default=lambda self: self.env.user
    )
    weather = fields.Selection(
        [
            ("clear", "صحو"),
            ("cloudy", "غائم"),
            ("rain", "ممطر"),
            ("hot", "حار"),
            ("sandstorm", "عاصفة رملية"),
        ],
        string="الطقس",
        default="clear",
    )
    temperature = fields.Integer(string="درجة الحرارة °م")
    work_done = fields.Text(string="الأعمال المنفّذة")
    delays = fields.Text(string="المعوقات/التأخيرات")
    equipment = fields.Text(string="المعدات في الموقع")
    visitors = fields.Char(string="الزوار")
    labor_ids = fields.One2many(
        "rawasi.daily.report.labor", "report_id", string="العمالة"
    )
    total_workers = fields.Integer(
        string="إجمالي العمالة", compute="_compute_total_workers", store=True
    )
    state = fields.Selection(
        [("draft", "مسودة"), ("confirmed", "معتمد")],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_dsr_attachment_rel",
        "report_id",
        "attachment_id",
        string="الصور/المرفقات",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.daily.report"
                ) or "/"
        return super().create(vals_list)

    @api.depends("labor_ids.worker_count")
    def _compute_total_workers(self):
        for rep in self:
            rep.total_workers = sum(rep.labor_ids.mapped("worker_count"))

    def _report_xmlid(self):
        return "rawasi_construction.action_report_dsr"

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})


class RawasiDailyReportLabor(models.Model):
    _name = "rawasi.daily.report.labor"
    _description = "سطر عمالة في التقرير اليومي"

    report_id = fields.Many2one(
        "rawasi.daily.report", required=True, ondelete="cascade"
    )
    trade = fields.Char(string="التخصص", required=True)
    worker_count = fields.Integer(string="العدد", default=0)
    note = fields.Char(string="ملاحظة")
