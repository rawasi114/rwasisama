# -*- coding: utf-8 -*-
"""مقاول من الباطن (Subcontractor) — السجل التعريفي لمقاولي الباطن.

نموذج مبسَّط: بيانات تعريفية + بيانات بنكية + مرفقات، مع ربط بالعقود الفرعية.
يعتمد على مجموعات الصلاحيات القياسية بدل workflow.mixin في نسخة الإنتاج.
"""
from odoo import api, fields, models


class RawasiSubcontractor(models.Model):
    _name = "rawasi.subcontractor"
    _description = "مقاول من الباطن — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="الاسم التجاري", required=True, tracking=True)
    code = fields.Char(string="الرمز", default="جديد", readonly=True, copy=False, index=True)
    cr_number = fields.Char(string="السجل التجاري", tracking=True)
    vat_number = fields.Char(string="الرقم الضريبي", tracking=True)
    phone = fields.Char(string="الجوال")
    email = fields.Char(string="البريد الإلكتروني")
    specialization = fields.Char(string="التخصص")
    bank_name = fields.Char(string="البنك")
    iban = fields.Char(string="الآيبان")
    notes = fields.Text(string="ملاحظات")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_subcontractor_attachment_rel",
        "subcontractor_id",
        "attachment_id",
        string="المرفقات",
    )
    subcontract_ids = fields.One2many(
        "rawasi.subcontract", "subcontractor_id", string="العقود الفرعية"
    )
    subcontract_count = fields.Integer(
        string="عدد العقود", compute="_compute_subcontract_count"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals["code"] == "جديد":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.subcontractor")
                    or "جديد"
                )
        return super().create(vals_list)

    def _compute_subcontract_count(self):
        for rec in self:
            rec.subcontract_count = len(rec.subcontract_ids)

    def action_open_subcontracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "عقود %s" % self.name,
            "res_model": "rawasi.subcontract",
            "view_mode": "list,form",
            "domain": [("subcontractor_id", "=", self.id)],
            "context": {"default_subcontractor_id": self.id},
        }
