from odoo import models, fields


class Competitor(models.Model):
    _name = "rps.competitor"
    _description = "Competitor (Rawasi Pricing Intelligence)"
    _order = "threat_level desc, name"

    name = fields.Char(string="اسم المنافس", required=True, index=True)
    backend_id = fields.Char(string="Backend UUID", index=True)
    cr_number = fields.Char(string="السجل التجاري")
    classification_grade = fields.Char(string="التصنيف")
    threat_level = fields.Integer(string="درجة التهديد", default=5)
    total_wins_observed = fields.Integer(string="الفوز الملاحظ")
    total_appearances = fields.Integer(string="الظهور الكلي")
    win_rate = fields.Float(string="نسبة الفوز %")
    notes = fields.Text()
