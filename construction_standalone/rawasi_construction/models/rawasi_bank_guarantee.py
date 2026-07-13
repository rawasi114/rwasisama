# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RawasiBankGuarantee(models.Model):
    _name = "rawasi.bank.guarantee"
    _description = "ضمان بنكي (Bank Guarantee)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "expiry_date asc, id desc"

    name = fields.Char(string="الرقم الداخلي", default="/", readonly=True, copy=False)
    project_id = fields.Many2one("project.project", string="المشروع", tracking=True)
    competition_id = fields.Many2one("rawasi.competition", string="المنافسة")
    guarantee_type = fields.Selection(
        [
            ("bid_bond", "ضمان ابتدائي (دخول)"),
            ("performance", "ضمان نهائي (حسن تنفيذ)"),
            ("advance_payment", "ضمان دفعة مقدمة"),
            ("retention", "ضمان محتجزات"),
        ],
        string="نوع الضمان",
        required=True,
        default="performance",
        tracking=True,
    )
    bank_name = fields.Char(string="البنك", tracking=True)
    reference_no = fields.Char(string="رقم الضمان", tracking=True)
    beneficiary = fields.Char(string="المستفيد")
    amount = fields.Monetary(string="المبلغ", tracking=True)
    issue_date = fields.Date(string="تاريخ الإصدار", default=fields.Date.context_today)
    expiry_date = fields.Date(string="تاريخ الانتهاء", required=True, tracking=True)
    state = fields.Selection(
        [
            ("active", "ساري"),
            ("released", "مُفرج عنه"),
            ("claimed", "مُصادَر"),
            ("expired", "منتهٍ"),
        ],
        string="الحالة",
        default="active",
        required=True,
        tracking=True,
    )
    days_to_expiry = fields.Integer(
        string="أيام حتى الانتهاء", compute="_compute_expiry", store=True
    )
    expiry_state = fields.Selection(
        [("valid", "ساري"), ("soon", "قريب الانتهاء"), ("expired", "منتهٍ")],
        string="حالة الانتهاء",
        compute="_compute_expiry",
        store=True,
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    attachment_ids = fields.Many2many(
        "ir.attachment", "rawasi_bg_attachment_rel", "bg_id", "attachment_id",
        string="المرفقات",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.bank.guarantee"
                ) or "/"
        return super().create(vals_list)

    @api.depends("expiry_date")
    def _compute_expiry(self):
        today = fields.Date.context_today(self)
        for bg in self:
            if bg.expiry_date:
                delta = (bg.expiry_date - today).days
                bg.days_to_expiry = delta
                if delta < 0:
                    bg.expiry_state = "expired"
                elif delta <= 30:
                    bg.expiry_state = "soon"
                else:
                    bg.expiry_state = "valid"
            else:
                bg.days_to_expiry = 0
                bg.expiry_state = "valid"

    def _report_xmlid(self):
        return "rawasi_construction.action_report_bank_guarantee"

    def action_release(self):
        self._ensure_admin()
        self.write({"state": "released"})

    def action_claim(self):
        self._ensure_admin()
        self.write({"state": "claimed"})

    def action_set_active(self):
        self._ensure_admin()
        self.write({"state": "active"})

    @api.model
    def _cron_check_expiry(self):
        """مهمة دورية: توسم المنتهية وتنبّه على الضمانات السارية القريبة من الانتهاء."""
        today = fields.Date.context_today(self)
        # وسم المنتهية
        expired = self.search([
            ("state", "=", "active"), ("expiry_date", "<", today),
        ])
        expired.write({"state": "expired"})
        # تنبيه على القريبة من الانتهاء (خلال 30 يوماً)
        soon = self.search([
            ("state", "=", "active"),
            ("expiry_date", ">=", today),
            ("expiry_date", "<=", fields.Date.add(today, days=30)),
        ])
        for bg in soon:
            bg.message_post(body=_(
                "تنبيه: الضمان البنكي %s ينتهي في %s (خلال %s يوماً)."
            ) % (bg.reference_no or bg.name, bg.expiry_date, bg.days_to_expiry))
        return True
