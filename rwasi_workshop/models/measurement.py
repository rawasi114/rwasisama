from odoo import models, fields
from .base import WORKSHOP_SCOPE


# ============================================================
# RS-WS-10 — نموذج معاينة وتفصيل (Measurement Sheet)
# ============================================================
class MeasurementSheet(models.Model):
    _name = 'rwasi.measurement.sheet'
    _description = 'نموذج معاينة وتفصيل (RS-WS-10)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.measurement.sheet'

    site = fields.Char(string='المشروع / الموقع')
    department = fields.Selection(
        WORKSHOP_SCOPE, string='القسم المعني')
    survey_date = fields.Date(
        string='تاريخ المعاينة', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.measurement.line', 'sheet_id', string='القياسات')

    sketch = fields.Binary(string='رسم تفصيلي / مخطط')
    sketch_filename = fields.Char(string='اسم ملف الرسم')

    # القائم بالمعاينة
    surveyor_name = fields.Char(string='القائم بالمعاينة - الاسم')
    surveyor_date = fields.Date(string='القائم بالمعاينة - التاريخ')
    surveyor_signature = fields.Binary(string='القائم بالمعاينة - التوقيع')


class MeasurementLine(models.Model):
    _name = 'rwasi.measurement.line'
    _description = 'بند قياس'
    _order = 'sequence, id'

    sheet_id = fields.Many2one(
        'rwasi.measurement.sheet', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    location = fields.Char(string='المرجع / الموقع')
    element = fields.Char(string='وصف العنصر', required=True)
    length = fields.Float(string='الطول')
    width = fields.Float(string='العرض')
    height = fields.Float(string='الارتفاع')
    qty = fields.Float(string='العدد')
    total = fields.Float(string='الإجمالي')
    uom = fields.Char(string='الوحدة')
