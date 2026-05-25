# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiBoqItem(models.Model):
    _name = "rawasi.boq.item"
    _description = "بند جدول الكميات (النواة الذرية للنظام)"
    _order = "competition_id, sequence, id"

    competition_id = fields.Many2one(
        "rawasi.competition",
        string="المنافسة",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    serial = fields.Char(string="الرقم التسلسلي")
    category = fields.Char(string="الفئة", index=True)
    work_group = fields.Char(string="البند/المجموعة")
    name = fields.Text(string="وصف البند", required=True)
    specifications = fields.Text(string="المواصفات")

    unit_text = fields.Char(string="الوحدة (كما وردت)")
    unit_id = fields.Many2one("rawasi.unit", string="الوحدة")
    quantity = fields.Float(string="الكمية", default=0.0)

    mandatory_local = fields.Selection(
        [("yes", "نعم"), ("no", "لا")],
        string="منتج من القائمة الإلزامية",
    )
    construction_code = fields.Char(string="الرمز الإنشائي (كما ورد)")
    sbc_code_id = fields.Many2one("rawasi.sbc.code", string="رمز SBC")

    currency_id = fields.Many2one(
        related="competition_id.currency_id", store=True, readonly=True
    )
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    total_cost = fields.Monetary(
        string="إجمالي التكلفة", compute="_compute_totals", store=True
    )
    unit_price = fields.Monetary(string="سعر الوحدة")
    total_price = fields.Monetary(
        string="إجمالي السعر", compute="_compute_totals", store=True
    )
    margin_pct = fields.Float(
        string="هامش %", compute="_compute_totals", store=True
    )

    @api.depends("quantity", "unit_cost", "unit_price")
    def _compute_totals(self):
        for item in self:
            item.total_cost = item.quantity * item.unit_cost
            item.total_price = item.quantity * item.unit_price
            item.margin_pct = (
                (item.unit_price - item.unit_cost) / item.unit_price * 100.0
                if item.unit_price
                else 0.0
            )
