"""Interactive pricing simulator — calls the backend's analytics engines."""

from odoo import models, fields, api


class PricingSimulator(models.TransientModel):
    _name = "rps.pricing.simulator"
    _description = "Pricing Simulator"

    tender_id = fields.Many2one("rps.tender", string="المنافسة")
    proposed_bid_amount = fields.Float(string="السعر المقترح", digits=(15, 2))
    estimated_cost = fields.Float(string="التكلفة المقدرة", digits=(15, 2))

    win_probability = fields.Float(
        string="احتمالية الفوز", readonly=True, digits=(5, 2)
    )
    expected_margin_pct = fields.Float(
        string="الهامش المتوقع %", readonly=True, digits=(5, 2)
    )
    expected_value = fields.Float(
        string="القيمة المتوقعة", readonly=True, digits=(15, 2)
    )
    recommendation = fields.Selection(
        [
            ("GO", "ادخل"),
            ("REVIEW", "راجع"),
            ("NO_GO", "لا تدخل"),
        ],
        readonly=True,
        string="التوصية",
    )

    def action_calculate(self):
        client = self.env["rps.api.client"]
        # In Phase 1 this stub returns a placeholder result — the real
        # implementation calls /analytics/optimal-bid + /analytics/go-no-go.
        for record in self:
            margin_pct = 0.0
            if record.proposed_bid_amount > 0 and record.estimated_cost > 0:
                margin_pct = (
                    (record.proposed_bid_amount - record.estimated_cost)
                    / record.proposed_bid_amount
                    * 100
                )
            record.expected_margin_pct = margin_pct
            record.win_probability = 0.0
            record.expected_value = 0.0
            record.recommendation = "REVIEW"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
