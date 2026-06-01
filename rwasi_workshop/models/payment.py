from odoo import models, fields, api


class CustomerPayment(models.Model):
    _name = 'rwasi.customer.payment'
    _description = 'دفعة عميل (مرتبطة بأمر البيع)'
    _order = 'date desc, id desc'

    name = fields.Char(string='المرجع', default='New', readonly=True, copy=False)
    sale_order_id = fields.Many2one(
        'sale.order', string='أمر البيع', required=True,
        ondelete='cascade', index=True)
    partner_id = fields.Many2one(
        related='sale_order_id.partner_id', string='العميل', store=True)
    company_id = fields.Many2one(
        related='sale_order_id.company_id', string='الشركة', store=True)
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id', string='العملة')
    date = fields.Date(
        string='تاريخ الدفعة', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(
        string='المبلغ', required=True, currency_field='currency_id')
    method = fields.Selection([
        ('cash', 'نقدي'),
        ('transfer', 'تحويل بنكي'),
        ('cheque', 'شيك'),
        ('other', 'أخرى'),
    ], string='طريقة الدفع', default='transfer')
    reference = fields.Char(string='مرجع/رقم العملية')
    note = fields.Char(string='ملاحظات')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rwasi.customer.payment') or 'New'
        return super().create(vals_list)
