from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    workshop_auto_mo = fields.Boolean(
        string='توليد أوامر التصنيع تلقائياً من المبيعات',
        default=True,
        help='عند تفعيله يُنشأ أمر تصنيع تلقائياً عند تأكيد أمر بيع يحتوي '
             'منتجات الورشة في هذه الشركة. أوقفه لشركات المقاولات العامة.')
    workshop_warehouse_id = fields.Many2one(
        'stock.warehouse', string='مستودع الورشة',
        help='عند تحديده تُعزَل مواد الورشة ومشترياتها في هذا المستودع '
             '(فحص التوفر والاستلام يتمّان فيه). اتركه فارغاً لاستخدام المخزون العام.')
