# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiRfi(models.Model):
    _name = "rawasi.rfi"
    _description = "طلب معلومات (Request For Information)"
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
    ncr_id = fields.Many2one(
        "rawasi.ncr", string="NCR المصدر", ondelete="set null",
        help="يُملأ تلقائياً عند تصعيد NCR إلى RFI.",
    )
    subject = fields.Char(string="الموضوع", required=True, tracking=True)
    question = fields.Text(string="الاستفسار", required=True)
    answer = fields.Text(string="الرد")
    raised_by_id = fields.Many2one(
        "res.users", string="مقدّم الطلب", default=lambda self: self.env.user
    )
    assigned_to_id = fields.Many2one("res.users", string="موجَّه إلى (الاستشاري)")
    priority = fields.Selection(
        [("low", "منخفضة"), ("medium", "متوسطة"), ("high", "عالية")],
        string="الأولوية",
        default="medium",
    )
    submitted_date = fields.Date(
        string="تاريخ الإرسال", default=fields.Date.context_today
    )
    date_required = fields.Date(string="تاريخ الحاجة للرد")
    date_answered = fields.Date(string="تاريخ الرد", readonly=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("submitted", "مُرسَل"),
            ("answered", "تمت الإجابة"),
            ("closed", "مغلق"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_rfi_attachment_rel",
        "rfi_id",
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
                    "rawasi.rfi"
                ) or "/"
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_answer(self):
        for rfi in self:
            if not rfi.answer:
                raise UserError(_("يلزم إدخال الرد قبل وسم الطلب كمُجاب."))
            rfi.write({"state": "answered", "date_answered": fields.Date.context_today(rfi)})

    def _report_xmlid(self):
        return "rawasi_construction.action_report_rfi"

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})
