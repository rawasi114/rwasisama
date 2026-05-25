# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiIndirectCost(models.Model):
    _name = "rawasi.indirect.cost"
    _description = "بند تكلفة غير مباشرة"
    _order = "sequence, id"

    competition_id = fields.Many2one(
        "rawasi.competition",
        string="المنافسة",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="البيان", required=True)
    compute_type = fields.Selection(
        [("percentage", "نسبة من التكلفة المباشرة"), ("fixed", "مبلغ ثابت")],
        string="النوع",
        default="percentage",
        required=True,
    )
    value = fields.Float(string="القيمة", help="نسبة مئوية أو مبلغ ثابت حسب النوع.")
    currency_id = fields.Many2one(related="competition_id.currency_id", store=True)
    amount = fields.Monetary(string="المبلغ", compute="_compute_amount", store=True)

    @api.depends(
        "compute_type", "value", "competition_id.boq_item_ids.total_cost"
    )
    def _compute_amount(self):
        # Base is summed directly from BOQ items (not from the competition's
        # stored amount_direct_cost) to avoid a circular compute dependency.
        for line in self:
            if line.compute_type == "percentage":
                base = sum(line.competition_id.boq_item_ids.mapped("total_cost"))
                line.amount = base * (line.value / 100.0)
            else:
                line.amount = line.value
