# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """إعدادات الموارد البشرية على مستوى الشركة (المنشأة).

    تُضاف هنا أرقام تعريف المنشأة لدى الجهات الرسمية وحسابات نهاية الخدمة
    الافتراضية، ليشترك فيها مسارا نهاية الخدمة وحماية الأجور.
    """

    _inherit = "res.company"

    # ------- تعريف المنشأة (لملف حماية الأجور) -------
    rawasi_mol_establishment_id = fields.Char(
        string="رقم المنشأة في مكتب العمل",
        help="رقم تعريف المنشأة لدى وزارة الموارد البشرية (يظهر في ملف حماية الأجور).",
    )
    rawasi_wps_bank_id = fields.Many2one(
        "res.partner.bank",
        string="حساب البنك للرواتب",
        help="حساب الشركة البنكي الذي تُصرف منه الرواتب في نظام حماية الأجور.",
    )

    # ------- حسابات نهاية الخدمة الافتراضية -------
    rawasi_eos_provision_account_id = fields.Many2one(
        "account.account",
        string="حساب مخصص نهاية الخدمة",
        help="الحساب المدين عند صرف المكافأة (مخصص مكافأة نهاية الخدمة).",
    )
    rawasi_eos_payable_account_id = fields.Many2one(
        "account.account",
        string="حساب مستحقات الموظفين",
        help="الحساب الدائن عند تكوين تسوية نهاية الخدمة (مستحق للموظف).",
    )
    rawasi_eos_journal_id = fields.Many2one(
        "account.journal",
        string="يومية نهاية الخدمة",
        domain="[('type', '=', 'general')]",
    )
