# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiVariationOrder(models.Model):
    """أمر تغيير (VO) — إضافة أو حذف من نطاق العقد."""

    _name = "rawasi.variation.order"
    _description = "أمر تغيير — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True, default="جديد")
    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    vo_type = fields.Selection(
        selection=[("addition", "إضافة"), ("omission", "حذف")],
        string="النوع",
        default="addition",
        required=True,
    )
    description = fields.Text(string="الوصف", required=True)
    amount = fields.Monetary(string="القيمة", currency_field="currency_id")
    signed_amount = fields.Monetary(
        compute="_compute_signed_amount", store=True, string="القيمة الموقّعة",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    request_date = fields.Date(string="تاريخ الطلب", default=fields.Date.context_today)
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("rejected", "مرفوض"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("amount", "vo_type")
    def _compute_signed_amount(self):
        for vo in self:
            vo.signed_amount = vo.amount if vo.vo_type == "addition" else -vo.amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.variation.order") or "جديد"
        return super().create(vals_list)

    def action_submit(self):
        self._require_state(["draft"])
        self.state = "submitted"

    def action_approve(self):
        self._require_state(["submitted"])
        self.state = "approved"

    def action_reject(self):
        self._require_state(["submitted"])
        self.state = "rejected"

    def action_reset_draft(self):
        self._require_state(["rejected"])
        self.state = "draft"

    def _require_state(self, allowed):
        for vo in self:
            if vo.state not in allowed:
                raise UserError("العملية غير مسموحة في الحالة الحالية.")
