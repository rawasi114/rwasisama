# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiWorkshopMaterialRequest(models.Model):
    """طلب مواد إنتاج الورشة — يرث سير الاعتماد الموحّد من القاعدة المجرّدة."""

    _name = "rawasi.workshop.material.request"
    _inherit = "rawasi.material.request.base"
    _description = "طلب مواد — ورشة"
    _mr_sequence_code = "rawasi.workshop.material.request"

    section_id = fields.Many2one(
        "rawasi.workshop.section", string="القسم", required=True, index=True
    )
    mo_id = fields.Many2one(
        "rawasi.workshop.mo", string="أمر التصنيع", required=True, index=True
    )
    line_ids = fields.One2many(
        "rawasi.workshop.material.request.line", "request_id", string="البنود"
    )
    picking_id = fields.Many2one("stock.picking", string="إذن الصرف", readonly=True, copy=False)

    def _do_issue(self):
        """يصرف مواد الإنتاج من مخزن القسم ويسجّل في التدقيق."""
        for req in self:
            self.env["rawasi.audit.trail"].log(
                req,
                "issue",
                detail="صرف مواد إنتاج للقسم %s / أمر %s"
                % (req.section_id.display_name, req.mo_id.display_name),
            )
        return True


class RawasiWorkshopMaterialRequestLine(models.Model):
    _name = "rawasi.workshop.material.request.line"
    _description = "بند طلب مواد — ورشة"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "rawasi.workshop.material.request",
        string="الطلب",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    product_id = fields.Many2one("product.product", string="المنتج")
    description = fields.Char(string="الوصف", required=True)
    qty = fields.Float(string="الكمية", default=1.0, required=True)
    uom_id = fields.Many2one("uom.uom", string="الوحدة", required=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id.id
