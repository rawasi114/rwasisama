# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class RawasiBankGuarantee(models.Model):
    """خطاب ضمان بنكي (ابتدائي / نهائي / دفعة مقدمة)."""

    _name = "rawasi.bank.guarantee"
    _description = "خطاب ضمان بنكي — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date"

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True, default="جديد")
    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    bank_id = fields.Many2one("res.partner", string="البنك")
    guarantee_type = fields.Selection(
        selection=[
            ("bid", "ابتدائي (دخول المنافسة)"),
            ("performance", "نهائي (حسن التنفيذ)"),
            ("advance", "دفعة مقدمة"),
        ],
        string="النوع",
        default="performance",
        required=True,
    )
    amount = fields.Monetary(string="القيمة", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    issue_date = fields.Date(string="تاريخ الإصدار", default=fields.Date.context_today)
    expiry_date = fields.Date(string="تاريخ الانتهاء", required=True)
    days_to_expiry = fields.Integer(
        compute="_compute_days_to_expiry", string="أيام للانتهاء", search="_search_days_to_expiry"
    )
    state = fields.Selection(
        selection=[
            ("active", "ساري"),
            ("expired", "منتهٍ"),
            ("released", "مُفرَج عنه"),
        ],
        string="الحالة",
        default="active",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("expiry_date")
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for bg in self:
            bg.days_to_expiry = (bg.expiry_date - today).days if bg.expiry_date else 0

    def _search_days_to_expiry(self, operator, value):
        # يدعم الفلترة على «أيام للانتهاء» عبر تحويلها لتاريخ
        today = fields.Date.context_today(self)
        target = fields.Date.to_string(today + timedelta(days=value or 0))
        date_op = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "=": "="}.get(operator, operator)
        return [("expiry_date", date_op, target)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.bank.guarantee") or "جديد"
        return super().create(vals_list)

    def action_release(self):
        self.write({"state": "released"})

    def action_set_expired(self):
        self.write({"state": "expired"})

    @api.model
    def _cron_check_expiry(self):
        """يحدّث الحالة ويُشعر بخطابات تنتهي خلال 30 يوماً."""
        today = fields.Date.context_today(self)
        active = self.search([("state", "=", "active")])
        hook = self.env["rawasi.notification.hook"]
        for bg in active:
            if bg.expiry_date and bg.expiry_date < today:
                bg.state = "expired"
            elif bg.expiry_date and (bg.expiry_date - today).days <= 30:
                hook.send(bg, "guarantee_expiring", extra="ينتهي بتاريخ %s" % bg.expiry_date)
        return True
