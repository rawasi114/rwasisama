# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    workshop_mo_ids = fields.One2many(
        'simple.mrp.order', 'sale_order_id', string="أوامر التصنيع")
    workshop_mo_count = fields.Integer(
        string="عدد أوامر التصنيع", compute='_compute_workshop_mo_count')
    workshop_mo_enabled = fields.Boolean(
        related='company_id.workshop_auto_mo', string="الورشة مفعّلة")

    @api.depends('workshop_mo_ids')
    def _compute_workshop_mo_count(self):
        for order in self:
            order.workshop_mo_count = len(order.workshop_mo_ids)

    def _is_workshop_company(self):
        self.ensure_one()
        return bool(self.company_id.workshop_auto_mo)

    def _workshop_mo_name(self, so_name):
        """يشتق رقم أمر التصنيع من رقم أمر البيع (مثل S00021 → MO00021)."""
        if not so_name:
            return False
        digits = re.sub(r'\D', '', so_name)
        if digits:
            return 'MO' + digits
        return 'MO' + so_name

    def _create_workshop_mos(self, force=False):
        MO = self.env['simple.mrp.order']
        for order in self:
            if not force and not order._is_workshop_company():
                continue
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                if order.workshop_mo_ids.filtered(lambda m: m.sale_line_id.id == line.id):
                    continue
                bom = line.product_id.bom_ids[:1]
                if not bom:
                    continue
                proposed = order._workshop_mo_name(order.name)
                name = proposed
                if proposed and MO.search_count([('name', '=', proposed)]):
                    name = False  # دع التسلسل يولّد رقماً فريداً
                vals = {
                    'product_id': line.product_id.id,
                    'bom_id': bom.id,
                    'product_qty': line.product_uom_qty,
                    'partner_id': order.partner_id.id,
                    'sale_order_id': order.id,
                    'sale_line_id': line.id,
                    'origin': order.name,
                    'company_id': order.company_id.id,
                }
                if name:
                    vals['name'] = name
                mo = MO.create(vals)
                mo.action_explode_bom()
        return True

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order._is_workshop_company():
                order._create_workshop_mos()
        return res

    def action_create_workshop_mos(self):
        self._create_workshop_mos(force=True)
        return self.action_view_workshop_mos()

    def action_view_workshop_mos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("أوامر التصنيع"),
            'res_model': 'simple.mrp.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }
