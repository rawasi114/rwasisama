# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiDocument(models.Model):
    _name = "rawasi.document"
    _description = "مستند المشروع (DMS)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"

    name = fields.Char(string="العنوان", required=True, tracking=True)
    reference = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    # رابط اختياري لبند جدول الكميات (المستند قد يخص بنداً بعينه)
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    document_type = fields.Selection(
        [
            ("drawing", "مخطط"),
            ("contract", "عقد/اتفاقية"),
            ("submittal", "مرفوعات"),
            ("method_statement", "بيان طريقة العمل"),
            ("report", "تقرير"),
            ("permit", "تصريح/ترخيص"),
            ("other", "أخرى"),
        ],
        string="نوع المستند",
        default="other",
        required=True,
        tracking=True,
    )
    revision = fields.Char(string="المراجعة", default="A")
    document_date = fields.Date(
        string="التاريخ", default=fields.Date.context_today
    )
    owner_id = fields.Many2one(
        "res.users", string="المسؤول", default=lambda self: self.env.user
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("under_review", "قيد المراجعة"),
            ("approved", "معتمد"),
            ("superseded", "ملغى/مستبدل"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_document_attachment_rel",
        "document_id",
        "attachment_id",
        string="الملفات",
    )
    attachment_count = fields.Integer(
        string="عدد الملفات", compute="_compute_attachment_count"
    )
    note = fields.Text(string="ملاحظات")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "/") == "/":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.document"
                ) or "/"
        return super().create(vals_list)

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for doc in self:
            doc.attachment_count = len(doc.attachment_ids)

    def _report_xmlid(self):
        return "rawasi_construction.action_report_document"

    def action_submit_review(self):
        self.write({"state": "under_review"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_supersede(self):
        self._ensure_admin()
        self.write({"state": "superseded"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})
