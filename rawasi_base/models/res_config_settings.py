# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------- الهوية البصرية (ألوان الدليل الرسمي) -------
    rawasi_brand_navy = fields.Char(
        string="الأزرق الداكن", config_parameter="rawasi_base.brand_navy", default="#253747"
    )
    rawasi_brand_gold = fields.Char(
        string="الذهبي", config_parameter="rawasi_base.brand_gold", default="#BD9B5E"
    )
    rawasi_brand_cream = fields.Char(
        string="الكريمي", config_parameter="rawasi_base.brand_cream", default="#F0E8DA"
    )

    # ------- توقيعات رقمية (على الشركة) -------
    rawasi_signature_site_engineer = fields.Binary(
        related="company_id.rawasi_signature_site_engineer", readonly=False
    )
    rawasi_signature_project_manager = fields.Binary(
        related="company_id.rawasi_signature_project_manager", readonly=False
    )
    rawasi_signature_technical = fields.Binary(
        related="company_id.rawasi_signature_technical", readonly=False
    )
    rawasi_signature_accountant = fields.Binary(
        related="company_id.rawasi_signature_accountant", readonly=False
    )

    # ------- الإشعارات -------
    rawasi_notification_provider = fields.Selection(
        selection=[("internal", "داخلي فقط"), ("whatsapp", "واتساب"), ("sms", "SMS")],
        string="مزوّد الإشعارات",
        config_parameter="rawasi_base.notification_provider",
        default="internal",
    )
    rawasi_whatsapp_endpoint = fields.Char(
        string="رابط واتساب", config_parameter="rawasi_base.whatsapp_endpoint"
    )
    rawasi_whatsapp_token = fields.Char(
        string="رمز واتساب", config_parameter="rawasi_base.whatsapp_token"
    )

    # ------- الأمان والاعتماد -------
    rawasi_require_pin_on_issue = fields.Boolean(
        string="طلب PIN عند الصرف",
        config_parameter="rawasi_base.require_pin_on_issue",
        default=True,
    )
    rawasi_escalation_hours = fields.Integer(
        string="ساعات التصعيد", config_parameter="rawasi_base.escalation_hours", default=48
    )

    # ------- الضريبة -------
    rawasi_default_vat_rate = fields.Float(
        string="نسبة ضريبة القيمة المضافة %",
        config_parameter="rawasi_base.default_vat_rate",
        default=15.0,
    )
