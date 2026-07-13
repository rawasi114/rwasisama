# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    """توسعة الموظف بتركيبة الأجر السعودية وبيانات حماية الأجور.

    نحتفظ بتفصيل الأجر (أساسي + سكن + بدلات أخرى) مباشرةً على الموظف لنكون
    مستقلّين عن موديول الرواتب (hr_payroll) ولنبقى صالحين على Community.
    تركيبة الأجر هذه هي أساس احتساب مكافأة نهاية الخدمة وملف حماية الأجور معاً.
    """

    _inherit = "hr.employee"

    rawasi_basic_wage = fields.Monetary(
        string="الأجر الأساسي", currency_field="currency_id", tracking=True
    )
    rawasi_housing_allowance = fields.Monetary(
        string="بدل السكن", currency_field="currency_id", tracking=True
    )
    rawasi_other_allowance = fields.Monetary(
        string="بدلات أخرى", currency_field="currency_id", tracking=True
    )
    rawasi_total_wage = fields.Monetary(
        string="إجمالي الأجر",
        currency_field="currency_id",
        compute="_compute_rawasi_total_wage",
        store=True,
        help="الأجر الأساسي + بدل السكن + البدلات الأخرى. هو وعاء احتساب نهاية الخدمة.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )

    # ------- بيانات نهاية الخدمة -------
    rawasi_join_date = fields.Date(
        string="تاريخ الالتحاق",
        help="تاريخ بداية الخدمة؛ أساس احتساب مدة الخدمة والمخصص الشهري.",
    )
    rawasi_eos_accrued = fields.Monetary(
        string="مخصص نهاية الخدمة المتراكم",
        currency_field="currency_id",
        readonly=True,
        help="إجمالي ما رُحِّل من مخصص شهري لنهاية الخدمة لهذا الموظف حتى الآن.",
    )

    # ------- بيانات حماية الأجور (مدد/WPS) -------
    rawasi_mol_number = fields.Char(
        string="رقم العامل في مكتب العمل",
        help="رقم تعريف العامل لدى وزارة الموارد البشرية (مطلوب في ملف حماية الأجور).",
    )
    rawasi_bank_iban = fields.Char(string="الآيبان (IBAN)")
    rawasi_bank_code = fields.Char(
        string="رمز البنك", help="رمز البنك المستلِم (يستخدم في ملف حماية الأجور)."
    )

    @api.depends("rawasi_basic_wage", "rawasi_housing_allowance", "rawasi_other_allowance")
    def _compute_rawasi_total_wage(self):
        for emp in self:
            emp.rawasi_total_wage = (
                (emp.rawasi_basic_wage or 0.0)
                + (emp.rawasi_housing_allowance or 0.0)
                + (emp.rawasi_other_allowance or 0.0)
            )

    def _rawasi_eos_wage_base(self, policy=None):
        """وعاء أجر نهاية الخدمة وفق السياسة المعطاة (أو سياسة الشركة)."""
        self.ensure_one()
        policy = policy or self.company_id.rawasi_eos_wage_base_policy or "full"
        if policy == "basic":
            return self.rawasi_basic_wage or 0.0
        if policy == "basic_housing":
            return (self.rawasi_basic_wage or 0.0) + (self.rawasi_housing_allowance or 0.0)
        return self.rawasi_total_wage or 0.0
