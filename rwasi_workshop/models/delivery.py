from odoo import models, fields, api, _
from odoo.exceptions import UserError


# ============================================================
# RS-WS-19 — إذن خروج وتسليم (Delivery / Gate Pass Note)
# ============================================================
class DeliveryNote(models.Model):
    _name = 'rwasi.delivery.note'
    _description = 'إذن خروج وتسليم (RS-WS-19)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.delivery.note'

    @api.model_create_multi
    def create(self, vals_list):
        # دورة مغلقة: يُنشأ أمر التسليم تلقائياً عند إنهاء التصنيع فقط
        if not self.env.context.get('from_work_order'):
            raise UserError(_(
                'لا يمكن إنشاء أمر تسليم يدوياً. يُنشأ تلقائياً عند إنهاء التصنيع في أمر التصنيع.'))
        return super().create(vals_list)

    work_order_id = fields.Many2one('rwasi.work.order', string='أمر التشغيل')
    site = fields.Char(string='المشروع / الموقع')
    consignee = fields.Char(string='جهة الاستلام')
    out_date = fields.Date(
        string='تاريخ الخروج', default=fields.Date.context_today)

    line_ids = fields.One2many(
        'rwasi.delivery.line', 'note_id', string='المواد المسلَّمة')

    # بيانات النقل
    driver = fields.Char(string='السائق')
    driver_id_no = fields.Char(string='رقم الهوية')
    plate = fields.Char(string='رقم اللوحة')
    carrier = fields.Char(string='شركة النقل')

    # أمين المستودع / المستلم / حارس البوابة
    storekeeper_name = fields.Char(string='أمين المستودع - الاسم')
    storekeeper_date = fields.Date(string='أمين المستودع - التاريخ')
    storekeeper_signature = fields.Binary(string='أمين المستودع - التوقيع')
    consignee_name = fields.Char(string='المستلم - الاسم')
    consignee_phone = fields.Char(string='المستلم - الهاتف')
    consignee_signature = fields.Binary(string='المستلم - التوقيع')
    gate_security_name = fields.Char(string='حارس البوابة - الاسم')
    gate_security_signature = fields.Binary(string='حارس البوابة - التوقيع')


class DeliveryLine(models.Model):
    _name = 'rwasi.delivery.line'
    _description = 'بند مواد مسلَّمة'
    _order = 'sequence, id'

    note_id = fields.Many2one(
        'rwasi.delivery.note', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    description = fields.Char(string='الوصف', required=True)
    item_ref = fields.Char(string='رقم البند')
    qty = fields.Float(string='الكمية')
    uom = fields.Char(string='الوحدة')
    packing = fields.Char(string='حالة التغليف')
