# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiBom(models.Model):
    """قائمة مواد (BoM) لبند مرجعي — تُحدّد مكوّنات إنتاجه/تنفيذه.

    تُستخدم في المقاولات لتقدير مواد البند، وفي التصنيع الداخلي بالورشة
    (المرحلة 7) كأساس لاستهلاك مواد الإنتاج.
    """

    _name = "rawasi.bom"
    _description = "قائمة مواد — رواسي"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="الاسم", required=True, tracking=True)
    code = fields.Char(string="الرمز", copy=False)
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المُنتَج", required=True, tracking=True
    )
    product_qty = fields.Float(string="الكمية المُنتَجة", default=1.0)
    uom_id = fields.Many2one(related="reference_item_id.uom_id", string="الوحدة")
    line_ids = fields.One2many("rawasi.bom.line", "bom_id", string="المكوّنات")
    total_cost = fields.Monetary(
        compute="_compute_total_cost", store=True, string="تكلفة المكوّنات",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("line_ids.subtotal")
    def _compute_total_cost(self):
        for bom in self:
            bom.total_cost = sum(bom.line_ids.mapped("subtotal"))


class RawasiBomLine(models.Model):
    _name = "rawasi.bom.line"
    _description = "مكوّن قائمة مواد — رواسي"
    _order = "bom_id, sequence, id"

    bom_id = fields.Many2one(
        "rawasi.bom", string="القائمة", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    component_item_id = fields.Many2one(
        "rawasi.reference.item", string="المكوّن", required=True
    )
    qty = fields.Float(string="الكمية", default=1.0, required=True)
    uom_id = fields.Many2one(related="component_item_id.uom_id", string="الوحدة")
    unit_cost = fields.Monetary(
        related="component_item_id.standard_cost", string="تكلفة الوحدة",
        currency_field="currency_id",
    )
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="الإجمالي", currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="bom_id.currency_id", string="العملة")

    @api.depends("qty", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_cost
