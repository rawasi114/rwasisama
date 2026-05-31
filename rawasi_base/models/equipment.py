# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiEquipment(models.Model):
    """الأصول الثابتة الموحَّدة (مكتب، سيارات، آلات ورشة، أدوات موقع، كاميرات).

    يُعرَّف في rawasi_base ليشترك فيه موديولا المقاولات والورشة. يضيف كل موديول
    فرعي حقوله الخاصة عبر الوراثة (project_id في المقاولات، workshop_section_id
    في الورشة).
    """

    _name = "rawasi.equipment"
    _description = "أصل ثابت — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code"

    name = fields.Char(string="الاسم", required=True, tracking=True)
    code = fields.Char(
        string="الرمز",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("rawasi.equipment") or "/",
    )
    category = fields.Selection(
        selection=[
            ("office_furniture", "أثاث مكتبي"),
            ("office_electronics", "أجهزة مكتبية"),
            ("vehicle", "سيارة"),
            ("workshop_machine", "آلة ورشة"),
            ("site_tool", "أداة موقع"),
            ("camera_system", "نظام كاميرات"),
        ],
        string="الفئة",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )
    purchase_price = fields.Monetary(string="سعر الشراء", currency_field="currency_id")
    purchase_date = fields.Date(string="تاريخ الشراء")
    custodian_user_id = fields.Many2one("res.users", string="في عهدة", tracking=True)
    location_text = fields.Char(string="الموقع")
    plate_number = fields.Char(string="رقم اللوحة")
    model = fields.Char(string="الموديل")
    serial_number = fields.Char(string="الرقم التسلسلي")
    notes = fields.Text(string="ملاحظات")
    asset_account_id = fields.Many2one(
        "account.account",
        string="حساب الأصل",
        domain="[('account_type', '=', 'asset_fixed')]",
    )
    depreciation_account_id = fields.Many2one(
        "account.account",
        string="حساب مجمَّع الإهلاك",
        domain="[('code', '=like', '112%')]",
    )
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        default=lambda self: self.env.company.id,
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز الأصل يجب أن يكون فريداً.",
    )

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "[%s] %s" % (rec.code, rec.name) if rec.code else (rec.name or "")
