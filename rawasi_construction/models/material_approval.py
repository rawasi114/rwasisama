# -*- coding: utf-8 -*-
"""اعتماد المواد (Material Approval Submittal - MAS).

نموذج مبسَّط لاعتماد المواد المقدَّمة للاستشاري قبل التوريد. لكل اعتماد بند مرجعي
من جدول الكميات، ومرفقات (كتالوجات/شهادات)، وحالة تعكس قرار الاستشاري:
معتمد / معتمد مع ملاحظات / مرفوض / إعادة تقديم.

تبسيط مقصود مقارنةً بنسخة الإنتاج: لا يعتمد على workflow.mixin، بل على مجموعات
الصلاحيات القياسية؛ ودمج PDF اختياري عبر زر منفصل دون تقرير QWeb للغلاف.
"""
import base64

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.pdf import merge_pdf


class RawasiMaterialApproval(models.Model):
    """طلب اعتماد مواد — يُقدَّم للاستشاري لاعتماد مادة قبل توريدها."""

    _name = "rawasi.material.approval"
    _description = "اعتماد مواد — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="المرجع", required=True, copy=False, readonly=True, default="جديد"
    )
    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    boq_item_id = fields.Many2one(
        "rawasi.boq.item",
        string="بند جدول الكميات",
        required=True,
    )
    material_name = fields.Char(string="اسم المادة", required=True)
    manufacturer = fields.Char(string="الشركة الصانعة")
    supplier_id = fields.Many2one("res.partner", string="المورّد")
    consultant_id = fields.Many2one("res.partner", string="الاستشاري")
    submittal_date = fields.Date(
        string="تاريخ التقديم", default=fields.Date.context_today
    )
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("approved_as_noted", "معتمد مع ملاحظات"),
            ("rejected", "مرفوض"),
            ("resubmit", "إعادة تقديم"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
    )
    consultant_remarks = fields.Text(string="ملاحظات الاستشاري")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_material_approval_attachment_rel",
        "approval_id",
        "attachment_id",
        string="المرفقات",
    )
    merged_pdf = fields.Binary(string="ملف PDF مدمج", attachment=True)
    merged_pdf_name = fields.Char(string="اسم الملف المدمج")
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.material.approval")
                    or "جديد"
                )
        return super().create(vals_list)

    def action_submit(self):
        self._require_state(["draft", "resubmit"])
        self.state = "submitted"

    def action_approve(self):
        self._require_state(["submitted"])
        self.state = "approved"

    def action_approve_as_noted(self):
        self._require_state(["submitted"])
        self.state = "approved_as_noted"

    def action_reject(self):
        self._require_state(["submitted"])
        self.state = "rejected"

    def action_request_resubmit(self):
        self._require_state(["submitted"])
        self.state = "resubmit"

    def action_reset_to_draft(self):
        self._require_state(["rejected", "resubmit"])
        self.state = "draft"

    def _require_state(self, allowed):
        for rec in self:
            if rec.state not in allowed:
                raise UserError("العملية غير مسموحة في الحالة الحالية.")

    def action_merge_attachments_pdf(self):
        """يدمج مرفقات PDF في ملف واحد (اختياري). يتجاهل المرفقات غير PDF."""
        self.ensure_one()
        pdf_attachments = self.attachment_ids.filtered(
            lambda a: (a.mimetype or "").lower() == "application/pdf"
        )
        if not pdf_attachments:
            raise UserError("لا توجد مرفقات بصيغة PDF لدمجها.")
        streams = [a.raw for a in pdf_attachments if a.raw]
        merged = merge_pdf(streams)
        self.merged_pdf = base64.b64encode(merged) if merged else False
        self.merged_pdf_name = "%s-merged.pdf" % (self.name or "approval")
        return True
