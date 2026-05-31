# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    workshop_mo_ids = fields.One2many(
        "rawasi.workshop.mo", "sale_order_id", string="أوامر تصنيع الورشة"
    )
    workshop_mo_count = fields.Integer(
        compute="_compute_workshop_mo_count", string="عدد أوامر التصنيع"
    )

    def _compute_workshop_mo_count(self):
        for order in self:
            order.workshop_mo_count = len(order.workshop_mo_ids)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._create_workshop_mos()
        return res

    def _create_workshop_mos(self):
        """ينشئ أمر تصنيع ورشة للمنتجات المعلَّمة «يُصنَّع في الورشة»، مجمَّعة بالقسم."""
        self.ensure_one()
        Mo = self.env["rawasi.workshop.mo"]
        by_section = {}
        for line in self.order_line:
            tmpl = line.product_id.product_tmpl_id
            if not tmpl.rawasi_produce_in_workshop:
                continue
            section = tmpl.rawasi_workshop_section_id
            if not section:
                continue
            by_section.setdefault(section, []).append(line)
        created = self.env["rawasi.workshop.mo"]
        for section, lines in by_section.items():
            mo = Mo.create(
                {
                    "section_id": section.id,
                    "partner_id": self.partner_id.id,
                    "sale_order_id": self.id,
                    "product_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": line.product_id.id,
                                "description": line.name,
                                "qty": line.product_uom_qty,
                                "uom_id": line.product_uom.id,
                                "unit_price": line.price_unit,
                            },
                        )
                        for line in lines
                    ],
                }
            )
            created |= mo
        return created

    def action_view_workshop_mos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "أوامر تصنيع الورشة",
            "res_model": "rawasi.workshop.mo",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
        }
