# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import stock_ops


class SimpleMrpOrder(models.Model):
    _name = 'simple.mrp.order'
    _description = "أمر تصنيع"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    product_id = fields.Many2one(
        'product.product', string="المنتج", required=True, tracking=True)
    bom_id = fields.Many2one('simple.mrp.bom', string="قائمة المواد", tracking=True)
    product_qty = fields.Float(string="الكمية", default=1.0, tracking=True)
    uom_name = fields.Char(related='product_id.uom_id.name', string="الوحدة")
    date_planned = fields.Date(
        string="التاريخ المخطط", default=fields.Date.context_today, tracking=True)
    date_started = fields.Datetime(string="تاريخ بدء التصنيع", readonly=True, copy=False)
    origin = fields.Char(string="المصدر", copy=False)

    sale_order_id = fields.Many2one(
        'sale.order', string="أمر البيع", ondelete='set null', copy=False)
    sale_line_id = fields.Many2one(
        'sale.order.line', string="بند البيع", ondelete='set null', copy=False)
    partner_id = fields.Many2one('res.partner', string="العميل", tracking=True)

    component_line_ids = fields.One2many(
        'simple.mrp.order.line', 'order_id', string="المكوّنات")
    availability_ok = fields.Boolean(
        string="المكوّنات متوفرة", compute='_compute_availability')

    state = fields.Selection([
        ('draft', "مسودة"),
        ('confirmed', "مؤكد"),
        ('progress', "قيد التصنيع"),
        ('done', "تم التصنيع"),
        ('delivered', "تم التسليم"),
        ('closed', "مغلق"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True, group_expand='_expand_states')

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    purchase_request_count = fields.Integer(compute='_compute_counts')
    has_pending_receipt = fields.Boolean(compute='_compute_counts')
    quality_check_count = fields.Integer(compute='_compute_counts')
    delivery_count = fields.Integer(compute='_compute_counts')
    closeout_count = fields.Integer(compute='_compute_counts')

    @api.model
    def _expand_states(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

    @api.depends('component_line_ids.available_qty', 'component_line_ids.qty')
    def _compute_availability(self):
        for order in self:
            order.availability_ok = bool(order.component_line_ids) and all(
                line.available_qty >= line.qty for line in order.component_line_ids)

    def _compute_counts(self):
        PR = self.env['simple.mrp.purchase.request']
        QC = self.env['simple.mrp.quality.check']
        DO = self.env['simple.mrp.delivery']
        CO = self.env['simple.mrp.closeout']
        for order in self:
            prs = PR.search([('order_id', '=', order.id)])
            order.purchase_request_count = len(prs)
            order.has_pending_receipt = any(
                p.state in ('draft', 'confirmed', 'partial') for p in prs)
            order.quality_check_count = QC.search_count([('order_id', '=', order.id)])
            order.delivery_count = DO.search_count([('order_id', '=', order.id)])
            order.closeout_count = CO.search_count([('order_id', '=', order.id)])

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for order in self:
            if order.product_id:
                bom = order.product_id.bom_ids[:1]
                order.bom_id = bom.id if bom else False

    @api.onchange('bom_id')
    def _onchange_bom(self):
        for order in self:
            if order.bom_id and order.bom_id.product_qty:
                pass

    def action_explode_bom(self):
        for order in self:
            if not order.bom_id:
                raise UserError(_("اختر قائمة مواد أولاً."))
            order.component_line_ids.unlink()
            base = order.bom_id.product_qty or 1.0
            factor = (order.product_qty or 1.0) / base
            lines = []
            for bline in order.bom_id.line_ids:
                lines.append((0, 0, {
                    'component_id': bline.component_id.id,
                    'qty': bline.qty * factor,
                }))
            order.component_line_ids = lines
        return True

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                continue
            if not order.component_line_ids:
                raise UserError(
                    _("لا يمكن تأكيد أمر تصنيع بدون مكوّنات. استخدم \"تفجير قائمة المواد\"."))
            order.state = 'confirmed'
        return True

    def action_check_availability(self):
        self.ensure_one()
        shortages = self.component_line_ids.filtered(
            lambda l: l.available_qty < l.qty)
        if not shortages:
            message = _("جميع المكوّنات متوفرة بالمخزون.")
            kind = 'success'
        else:
            details = "\n".join(
                "- %s: مطلوب %.2f / متاح %.2f" % (
                    l.component_id.display_name, l.qty, l.available_qty)
                for l in shortages)
            message = _("توجد مكوّنات ناقصة:\n%s") % details
            kind = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _("توفر المكوّنات"), 'message': message,
                       'type': kind, 'sticky': bool(shortages)},
        }

    def action_start_production(self):
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_("يجب تأكيد الأمر قبل بدء التصنيع."))
            if not order.availability_ok:
                raise UserError(
                    _("لا يمكن بدء التصنيع: بعض المكوّنات غير متوفرة بالمخزون. "
                      "اطلب شراءها أو وفّرها أولاً."))
            order.state = 'progress'
            order.date_started = fields.Datetime.now()
        return True

    def action_produce(self):
        for order in self:
            if order.state != 'progress':
                raise UserError(_("يجب أن يكون الأمر قيد التصنيع."))
            for line in order.component_line_ids:
                if line.available_qty < line.qty:
                    raise UserError(
                        _("المكوّن %s غير كافٍ بالمخزون.") % line.component_id.display_name)
            for line in order.component_line_ids:
                stock_ops.change_stock(self.env, line.component_id, -line.qty)
            stock_ops.change_stock(self.env, order.product_id, order.product_qty)
            order.state = 'done'
        return True

    def action_request_purchase(self):
        self.ensure_one()
        shortages = self.component_line_ids.filtered(
            lambda l: l.available_qty < l.qty)
        if not shortages:
            raise UserError(_("لا توجد مكوّنات ناقصة لطلب شرائها."))
        lines = []
        for l in shortages:
            need = l.qty - l.available_qty
            lines.append((0, 0, {
                'product_id': l.component_id.id,
                'qty': need,
                'unit_cost': l.component_id.standard_price,
            }))
        pr = self.env['simple.mrp.purchase.request'].create({
            'order_id': self.id,
            'origin': self.name,
            'line_ids': lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'simple.mrp.purchase.request',
            'res_id': pr.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_deliver(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("لا يمكن التسليم إلا بعد إتمام التصنيع."))
        do = self.env['simple.mrp.delivery'].create({
            'order_id': self.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'qty': self.product_qty,
                'unit_price': self.product_id.list_price,
            })],
        })
        self.state = 'delivered'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'simple.mrp.delivery',
            'res_id': do.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_close_project(self):
        self.ensure_one()
        if self.state != 'delivered':
            raise UserError(_("لا يمكن إغلاق المشروع إلا بعد التسليم."))
        co = self.env['simple.mrp.closeout'].create({
            'order_id': self.id,
            'project': self.origin or self.name,
            'client': self.partner_id.name,
        })
        self.state = 'closed'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'simple.mrp.closeout',
            'res_id': co.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        for order in self:
            if order.state in ('delivered', 'closed'):
                raise UserError(
                    _("لا يمكن إلغاء أمر تم تسليمه أو إغلاقه."))
            order.state = 'cancel'
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    # ----- أزرار العرض -----
    def _view_action(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_sales(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("أمر البيع"),
            'res_model': 'sale.order',
            'view_mode': 'form,list',
            'res_id': self.sale_order_id.id,
            'domain': [('id', '=', self.sale_order_id.id)],
        }

    def action_view_purchases(self):
        return self._view_action('simple.mrp.purchase.request', _("طلبات الشراء"))

    def action_view_quality(self):
        return self._view_action('simple.mrp.quality.check', _("فحوص الجودة"))

    def action_view_deliveries(self):
        return self._view_action('simple.mrp.delivery', _("التسليمات"))

    def action_view_closeouts(self):
        return self._view_action('simple.mrp.closeout', _("إغلاق المشروع"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.order') or 'New'
        return super().create(vals_list)

    def unlink(self):
        if not self.env.is_superuser():
            raise UserError(
                _("لا يُسمح بحذف أوامر التصنيع. استخدم \"إلغاء\" بدلاً من الحذف."))
        return super().unlink()


class SimpleMrpOrderLine(models.Model):
    _name = 'simple.mrp.order.line'
    _description = "مكوّن أمر التصنيع"
    _order = 'sequence, id'

    sequence = fields.Integer(string="م.", default=10)
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", required=True, ondelete='cascade')
    component_id = fields.Many2one(
        'product.product', string="المكوّن", required=True)
    qty = fields.Float(string="الكمية المطلوبة", default=1.0)
    uom_name = fields.Char(related='component_id.uom_id.name', string="الوحدة")
    available_qty = fields.Float(
        string="المتاح بالمخزون", compute='_compute_available_qty')

    @api.depends('component_id')
    def _compute_available_qty(self):
        for line in self:
            line.available_qty = stock_ops.available_qty(self.env, line.component_id)
