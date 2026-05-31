# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiWorkshopSection(models.Model):
    """قسم ورشة (نجارة CARP / حدادة STEEL ...).

    لكل قسم حساب تحليلي ضمن خطة «أقسام الورشة» ومواقع مخزون للإنتاج والمواد.
    """

    _name = "rawasi.workshop.section"
    _description = "قسم ورشة — رواسي"
    _order = "code, name"

    name = fields.Char(string="الاسم", required=True)
    code = fields.Char(string="الرمز", required=True, help="مثل CARP / STEEL")
    responsible_user_id = fields.Many2one("res.users", string="المشرف المسؤول")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="الحساب التحليلي"
    )
    stock_location_id = fields.Many2one("stock.location", string="مخزن المواد")
    production_location_id = fields.Many2one("stock.location", string="موقع الإنتاج")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز القسم يجب أن يكون فريداً.",
    )

    @api.depends("name", "code")
    def _compute_display_name(self):
        for sec in self:
            sec.display_name = "[%s] %s" % (sec.code, sec.name) if sec.code else sec.name
