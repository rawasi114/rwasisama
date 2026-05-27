"""Odoo wrapper around tender records living in the FastAPI backend.

For Phase 1 this is a thin read/cache layer — the source of truth is the
FastAPI service. Records here mirror the backend rather than duplicate it.
"""

from odoo import models, fields, api


class Tender(models.Model):
    _name = "rps.tender"
    _description = "Awarded Tender (Rawasi Pricing Intelligence)"
    _order = "award_date desc"

    name = fields.Char(string="عنوان المنافسة", required=True)
    etimad_tender_id = fields.Char(string="رقم اعتماد", index=True)
    backend_id = fields.Char(string="Backend UUID", index=True)
    government_entity = fields.Char(string="الجهة الحكومية")
    sub_entity_name = fields.Char(string="الجهة الفرعية")
    region_name = fields.Char(string="المنطقة")
    award_date = fields.Date(string="تاريخ الترسية", required=True)
    award_value = fields.Float(string="قيمة الترسية", required=True, digits=(15, 2))
    winner_name = fields.Char(string="الفائز")
    total_bidders = fields.Integer(string="عدد المتنافسين")
    rawasi_participated = fields.Boolean(string="شاركت رواسي")
    rawasi_rank = fields.Integer(string="رتبة رواسي")
    rawasi_bid_amount = fields.Float(string="عرض رواسي", digits=(15, 2))
    notes = fields.Text(string="ملاحظات")
    data_quality_score = fields.Float(string="جودة البيانات")
    has_full_boq = fields.Boolean(string="لديه جدول كميات كامل")

    @api.constrains("award_value")
    def _check_award_value(self):
        for record in self:
            if record.award_value is not None and record.award_value <= 0:
                raise ValueError("Award value must be positive.")
