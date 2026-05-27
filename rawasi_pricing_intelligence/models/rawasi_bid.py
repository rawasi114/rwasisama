from odoo import models, fields


class RawasiBid(models.Model):
    _name = "rps.rawasi.bid"
    _description = "Rawasi Bid (Rawasi Pricing Intelligence)"
    _order = "submission_date desc"

    name = fields.Char(string="مرجع العرض", required=True)
    tender_id = fields.Many2one("rps.tender", string="المنافسة")
    backend_id = fields.Char(string="Backend UUID", index=True)
    bid_total_amount = fields.Float(string="إجمالي عرض رواسي", digits=(15, 2))
    submission_date = fields.Date(string="تاريخ التقديم")
    final_rank = fields.Integer(string="الترتيب النهائي")
    won = fields.Boolean(string="فاز")
    pricing_strategy = fields.Selection(
        [
            ("aggressive", "عدواني"),
            ("balanced", "متوازن"),
            ("premium", "مرتفع"),
        ],
        string="استراتيجية التسعير",
    )
    target_margin_pct = fields.Float(string="الهامش المستهدف %")
    post_mortem_notes = fields.Text(string="ملاحظات ما بعد النتيجة")
