# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    rawasi_is_construction = fields.Boolean(string="مشروع مقاولات", default=False)
    rawasi_competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المصدر", readonly=True, copy=False
    )
    rawasi_code = fields.Char(string="رمز المشروع", copy=False)
    rawasi_contract_value = fields.Monetary(
        string="قيمة العقد", currency_field="rawasi_currency_id"
    )
    rawasi_currency_id = fields.Many2one(
        "res.currency",
        string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )
    rawasi_date_start = fields.Date(string="تاريخ البدء")
    rawasi_date_end = fields.Date(string="تاريخ الانتهاء التعاقدي")
    rawasi_main_location_id = fields.Many2one(
        "stock.location", string="المخزن الرئيسي للمشروع"
    )
    rawasi_boq_item_ids = fields.One2many(
        "rawasi.boq.item",
        related="rawasi_competition_id.boq_item_ids",
        string="جدول الكميات",
    )
