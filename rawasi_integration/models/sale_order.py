# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_internal_workshop = fields.Boolean(string="تصنيع داخلي", default=False, copy=False)
    internal_workshop_order_id = fields.Many2one(
        "rawasi.internal.workshop.order", string="أمر التصنيع الداخلي", copy=False
    )

    def _create_workshop_mos(self):
        """للأوامر الداخلية: ينشئ MO داخلياً (is_internal) مرتبطاً بأمر التصنيع الداخلي،
        ويتخطّى المسار القياسي القائم على علامة المنتج."""
        self.ensure_one()
        if self.is_internal_workshop and self.internal_workshop_order_id:
            return self._create_internal_workshop_mo()
        return super()._create_workshop_mos()

    def _create_internal_workshop_mo(self):
        self.ensure_one()
        iwo = self.internal_workshop_order_id
        mo = self.env["rawasi.workshop.mo"].create(
            {
                "section_id": iwo.section_id.id,
                "partner_id": self.partner_id.id,
                "sale_order_id": self.id,
                "internal_workshop_order_id": iwo.id,
                "is_internal": True,
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
                    for line in self.order_line
                    if line.product_id
                ],
            }
        )
        iwo.write({"workshop_mo_id": mo.id, "state": "in_production"})
        self.env["rawasi.notification.hook"].send(iwo, "internal_so_confirmed")
        return mo
