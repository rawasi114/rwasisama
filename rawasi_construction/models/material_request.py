# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiMaterialRequest(models.Model):
    """طلب مواد المقاولات — يرث سير الاعتماد الموحّد من القاعدة المجرّدة."""

    _name = "rawasi.material.request"
    _inherit = "rawasi.material.request.base"
    _description = "طلب مواد — مقاولات"
    _mr_sequence_code = "rawasi.material.request"

    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    procurement_type = fields.Selection(
        related="boq_item_id.procurement_type", string="مسار التوريد", store=True
    )
    line_ids = fields.One2many(
        "rawasi.material.request.line", "request_id", string="البنود"
    )
    location_dest_id = fields.Many2one(
        "stock.location", string="موقع التسليم (المشروع)"
    )
    picking_id = fields.Many2one("stock.picking", string="إذن الصرف", readonly=True, copy=False)
    amount_estimate = fields.Monetary(
        compute="_compute_amount_estimate", string="التكلفة التقديرية",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )

    @api.depends("line_ids.subtotal")
    def _compute_amount_estimate(self):
        for req in self:
            req.amount_estimate = sum(req.line_ids.mapped("subtotal"))

    @api.onchange("project_id")
    def _onchange_project_id(self):
        if self.project_id and self.project_id.rawasi_main_location_id:
            self.location_dest_id = self.project_id.rawasi_main_location_id.id

    # ------------------------------------------------------------------
    # تجاوز نقاط القاعدة المجرّدة
    # ------------------------------------------------------------------
    def _do_issue(self):
        """يصرف المواد للمشروع: ينشئ إذن صرف داخلي إن أمكن، ويسجّل في التدقيق."""
        for req in self:
            if req.location_dest_id and req.line_ids:
                picking = req._create_issue_picking()
                if picking:
                    req.picking_id = picking.id
            self.env["rawasi.audit.trail"].log(
                req, "issue", detail="صرف مواد للمشروع %s" % (req.project_id.display_name)
            )
        return True

    def _create_issue_picking(self):
        """ينشئ إذن صرف داخلي من مخزون عام إلى موقع المشروع (إن توفّرت الإعدادات)."""
        self.ensure_one()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        if not warehouse:
            return False
        picking_type = warehouse.int_type_id
        src = picking_type.default_location_src_id or warehouse.lot_stock_id
        dest = self.location_dest_id
        if not (picking_type and src and dest):
            return False
        moves = []
        for line in self.line_ids:
            if not line.product_id:
                continue
            moves.append(
                (
                    0,
                    0,
                    {
                        "name": line.description or line.product_id.display_name,
                        "product_id": line.product_id.id,
                        "product_uom_qty": line.qty,
                        "product_uom": line.uom_id.id,
                        "location_id": src.id,
                        "location_dest_id": dest.id,
                    },
                )
            )
        if not moves:
            return False
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "origin": self.name,
                "move_ids": moves,
            }
        )
        return picking


class RawasiMaterialRequestLine(models.Model):
    _name = "rawasi.material.request.line"
    _description = "بند طلب مواد — مقاولات"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "rawasi.material.request", string="الطلب", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    reference_item_id = fields.Many2one("rawasi.reference.item", string="البند المرجعي")
    product_id = fields.Many2one("product.product", string="المنتج")
    description = fields.Char(string="الوصف", required=True)
    qty = fields.Float(string="الكمية", default=1.0, required=True)
    uom_id = fields.Many2one("uom.uom", string="الوحدة", required=True)
    unit_cost = fields.Monetary(string="تكلفة الوحدة", currency_field="currency_id")
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="الإجمالي", currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="request_id.currency_id", string="العملة")

    @api.depends("qty", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_cost

    @api.onchange("reference_item_id")
    def _onchange_reference_item(self):
        if self.reference_item_id:
            ref = self.reference_item_id
            self.product_id = ref.product_id.id
            self.description = ref.name
            self.uom_id = ref.uom_id.id
            self.unit_cost = ref.standard_cost
