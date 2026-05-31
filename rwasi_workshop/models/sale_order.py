from odoo import models, fields, api, _
from .base import WORKSHOP_SCOPE


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_workshop_product = fields.Boolean(
        string='يُصنّع في الورشة',
        help='عند تفعيله يُنشأ أمر تصنيع تلقائياً عند تأكيد أمر بيع يحتوي هذا المنتج.')
    workshop_scope = fields.Selection(
        WORKSHOP_SCOPE, string='قسم التصنيع')
    workshop_material_ids = fields.One2many(
        'rwasi.product.material', 'product_tmpl_id', string='مواد التصنيع')


class ProductWorkshopMaterial(models.Model):
    _name = 'rwasi.product.material'
    _description = 'مادة خام لتصنيع المنتج'

    product_tmpl_id = fields.Many2one(
        'product.template', string='المنتج', required=True, ondelete='cascade')
    material_id = fields.Many2one(
        'product.product', string='المادة الخام', required=True,
        domain=[('purchase_ok', '=', True), ('sale_ok', '=', False)])
    qty = fields.Float(string='الكمية لكل وحدة', default=1.0)
    uom_name = fields.Char(
        related='material_id.uom_id.name', string='الوحدة')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    work_order_ids = fields.One2many(
        'rwasi.work.order', 'sale_order_id', string='أوامر التصنيع')
    work_order_count = fields.Integer(
        string='عدد أوامر التصنيع', compute='_compute_work_order_count')

    workshop_payment_ids = fields.One2many(
        'rwasi.customer.payment', 'sale_order_id', string='دفعات العميل')
    workshop_payment_count = fields.Integer(compute='_compute_workshop_payment')
    amount_paid = fields.Monetary(
        string='المُحصَّل', compute='_compute_workshop_payment',
        currency_field='currency_id')
    payment_ratio = fields.Float(
        string='نسبة السداد', compute='_compute_workshop_payment')

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for order in self:
            order.work_order_count = len(order.work_order_ids)

    @api.depends('workshop_payment_ids.amount', 'amount_total')
    def _compute_workshop_payment(self):
        for order in self:
            order.amount_paid = sum(order.workshop_payment_ids.mapped('amount'))
            order.workshop_payment_count = len(order.workshop_payment_ids)
            order.payment_ratio = (order.amount_paid / order.amount_total) \
                if order.amount_total else 0.0

    def action_view_workshop_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('دفعات العميل'),
            'res_model': 'rwasi.customer.payment',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._create_workshop_work_orders()
        return res

    def _create_workshop_work_orders(self):
        """ينشئ أمر تصنيع واحد فقط لأمر البيع (1:1)، وكل بند منتج ورشي
        يُضاف كبند تنفيذ (work job) داخل أمر التصنيع. البنود غير الورشية
        (خدمات/توريد عادي) تُتجاهل ولا تدخل أمر التصنيع."""
        self.ensure_one()
        if not self.company_id.workshop_auto_mo:
            return
        # اجمع البنود الورشية فقط (تجاهل display_type وغير-الورشية)
        workshop_lines = self.order_line.filtered(
            lambda l: not l.display_type
            and l.product_id
            and l.product_id.product_tmpl_id.is_workshop_product
        )
        if not workshop_lines:
            return

        # ابحث عن أمر تصنيع موجود لهذا أمر البيع (1:1)
        WorkOrder = self.env['rwasi.work.order'].sudo().with_context(from_sale_order=True)
        existing_mo = self.work_order_ids[:1]

        # بنود التنفيذ (work jobs) الجديدة فقط — البنود المُسجَّلة سابقاً تُحترم
        existing_sale_line_ids = (existing_mo.line_ids.mapped('sale_line_id').ids
                                  if existing_mo else [])
        new_jobs = []
        new_materials = []
        first_product = None
        for line in workshop_lines:
            if line.id in existing_sale_line_ids:
                continue
            product = line.product_id
            if first_product is None:
                first_product = product
            new_jobs.append((0, 0, {
                'sale_line_id': line.id,
                'product_id': product.id,
                'description': line.name or product.display_name,
                'qty': line.product_uom_qty,
                'uom': product.uom_id.name,
            }))
            for m in product.product_tmpl_id.workshop_material_ids:
                new_materials.append((0, 0, {
                    'material_id': m.material_id.id,
                    'qty_needed': m.qty * line.product_uom_qty,
                }))

        if not new_jobs:
            return  # كل البنود الورشية مُمثَّلة سلفاً

        if existing_mo:
            # توسعة أمر التصنيع القائم
            existing_mo.write({
                'line_ids': new_jobs,
                'material_line_ids': new_materials,
            })
        else:
            # إنشاء أمر تصنيع جديد واحد
            primary_product = first_product or workshop_lines[0].product_id
            WorkOrder.create({
                'sale_order_id': self.id,
                'partner_id': self.partner_id.id,
                'product_id': primary_product.id,
                'product_qty': sum(workshop_lines.mapped('product_uom_qty')) or 1.0,
                'scope_of_work': '\n'.join(workshop_lines.mapped('name')),
                'workshop_scope': primary_product.product_tmpl_id.workshop_scope,
                'project_ref': self.name,
                'line_ids': new_jobs,
                'material_line_ids': new_materials,
            })

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('أوامر التصنيع'),
            'res_model': 'rwasi.work.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }
