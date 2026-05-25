# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.pdf import merge_pdf


class RawasiMaterialApproval(models.Model):
    _name = "rawasi.material.approval"
    _description = "طلب اعتماد مادة (Material Approval Submission)"
    _inherit = ["mail.thread", "mail.activity.mixin", "rawasi.workflow.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    # القيد المعماري: اعتماد المادة يرتبط إلزامياً ببند جدول الكميات
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند جدول الكميات", required=True, tracking=True
    )
    material_name = fields.Char(string="المادة", required=True, tracking=True)
    manufacturer = fields.Char(string="المُصنّع")
    supplier = fields.Char(string="المورد")
    submittal_date = fields.Date(
        string="تاريخ الرفع", default=fields.Date.context_today, tracking=True
    )
    consultant_id = fields.Many2one("res.users", string="الاستشاري المراجِع")
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("submitted", "مقدَّم للاستشاري"),
            ("approved", "معتمد (A)"),
            ("approved_as_noted", "معتمد مع ملاحظات (B)"),
            ("rejected", "مرفوض (C)"),
            ("resubmit", "يُعاد رفعه (D)"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    consultant_remarks = fields.Text(string="ملاحظات الاستشاري")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_mas_attachment_rel",
        "mas_id",
        "attachment_id",
        string="المرفقات (كتالوجات/شهادات)",
    )
    merged_pdf = fields.Binary(string="ملف الاعتماد المدموج", attachment=True, copy=False)
    merged_pdf_name = fields.Char(string="اسم الملف المدموج", copy=False)
    note = fields.Text(string="ملاحظات")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.material.approval"
                ) or "/"
        return super().create(vals_list)

    # ── سير العمل ────────────────────────────────────────────────
    def action_submit(self):
        for mas in self:
            if not mas.material_name:
                raise UserError(_("يلزم تحديد اسم المادة قبل الرفع."))
            mas.state = "submitted"

    def action_approve(self):
        self.write({"state": "approved"})

    def action_approve_as_noted(self):
        self.write({"state": "approved_as_noted"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_request_resubmit(self):
        self.write({"state": "resubmit"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})

    # ── دمج PDF (الغلاف + المرفقات في ملف واحد) ──────────────────
    def _attachment_pdf_streams(self):
        """يجمع بايتات مرفقات PDF فقط (مرتبة) لدمجها."""
        self.ensure_one()
        streams = []
        for att in self.attachment_ids.sorted("id"):
            if att.mimetype == "application/pdf" and att.datas:
                streams.append(base64.b64decode(att.datas))
        return streams

    def action_generate_submittal_pdf(self):
        """يولّد غلاف الاعتماد (QWeb) ويدمجه مع مرفقات PDF في ملف واحد."""
        self.ensure_one()
        cover, _dummy = self.env["ir.actions.report"]._render_qweb_pdf(
            "rawasi_construction.action_report_mas_cover", res_ids=self.ids
        )
        streams = [cover] + self._attachment_pdf_streams()
        merged = merge_pdf(streams)
        self.merged_pdf = base64.b64encode(merged)
        self.merged_pdf_name = "MAS-%s.pdf" % (self.name or "submittal").replace("/", "-")
        self.message_post(body=_("تم توليد ملف الاعتماد المدموج (PDF)."))
        return True
