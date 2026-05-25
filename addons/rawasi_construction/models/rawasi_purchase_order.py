# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiPurchaseOrder(models.Model):
    _name = "rawasi.purchase.order"
    _description = "أمر شراء (Purchase Order)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="الرقم", required=True, copy=False, readonly=True, default="/")
    project_id = fields.Many2one("project.project", string="المشروع", required=True, tracking=True)
    mr_id = fields.Many2one("rawasi.material.request", string="طلب المواد", readonly=True)
    vendor_id = fields.Many2one("res.partner", string="المورّد", tracking=True)
    order_date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("confirmed", "مؤكَّد"),
            ("received", "مستلَم بالكامل"),
            ("cancelled", "ملغى"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many("rawasi.purchase.order.line", "order_id", string="السطور")
    note = fields.Text(string="ملاحظات")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount_total = fields.Monetary(string="الإجمالي", compute="_compute_amount_total", store=True)
    receipt_count = fields.Integer(compute="_compute_receipt_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.purchase.order"
                ) or "/"
        return super().create(vals_list)

    @api.depends("line_ids.amount_subtotal")
    def _compute_amount_total(self):
        for po in self:
            po.amount_total = sum(po.line_ids.mapped("amount_subtotal"))

    def _compute_receipt_count(self):
        for po in self:
            po.receipt_count = self.env["rawasi.goods.receipt"].search_count(
                [("order_id", "=", po.id)]
            )

    def action_confirm(self):
        for po in self:
            if not po.line_ids:
                raise UserError(_("لا يمكن تأكيد أمر شراء بلا سطور."))
            po.state = "confirmed"

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_create_grn(self):
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("لا يمكن الاستلام إلا من أمر شراء مؤكَّد."))
        grn = self.env["rawasi.goods.receipt"].create({
            "order_id": self.id,
            "line_ids": [
                (0, 0, {
                    "po_line_id": line.id,
                    "quantity": line.quantity - line.qty_received,
                })
                for line in self.line_ids
                if line.quantity - line.qty_received > 0
            ],
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "rawasi.goods.receipt",
            "res_id": grn.id,
            "view_mode": "form",
        }

    def action_open_receipts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("سندات الاستلام"),
            "res_model": "rawasi.goods.receipt",
            "view_mode": "list,form",
            "domain": [("order_id", "=", self.id)],
            "context": {"default_order_id": self.id},
        }


class RawasiPurchaseOrderLine(models.Model):
    _name = "rawasi.purchase.order.line"
    _description = "سطر أمر شراء"

    order_id = fields.Many2one("rawasi.purchase.order", required=True, ondelete="cascade")
    order_state = fields.Selection(related="order_id.state", store=True)
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات", required=True)
    description = fields.Char(string="الوصف")
    quantity = fields.Float(string="الكمية المطلوبة", default=1.0)
    unit_id = fields.Many2one(related="boq_item_id.unit_id", string="الوحدة")
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    currency_id = fields.Many2one(related="order_id.currency_id")
    amount_subtotal = fields.Monetary(string="الإجمالي", compute="_compute_amounts", store=True)
    grn_line_ids = fields.One2many("rawasi.goods.receipt.line", "po_line_id")
    qty_received = fields.Float(string="المستلَم", compute="_compute_received", store=True)
    amount_received = fields.Monetary(string="قيمة المستلَم", compute="_compute_received", store=True)
    amount_open = fields.Monetary(string="القيمة المفتوحة", compute="_compute_received", store=True)

    @api.depends("quantity", "unit_cost")
    def _compute_amounts(self):
        for line in self:
            line.amount_subtotal = line.quantity * line.unit_cost

    @api.depends(
        "quantity", "unit_cost",
        "grn_line_ids.quantity", "grn_line_ids.receipt_id.state",
    )
    def _compute_received(self):
        for line in self:
            received = sum(
                gl.quantity
                for gl in line.grn_line_ids
                if gl.receipt_id.state == "done"
            )
            line.qty_received = received
            line.amount_received = received * line.unit_cost
            line.amount_open = max(0.0, (line.quantity - received)) * line.unit_cost

    @api.onchange("boq_item_id")
    def _onchange_boq_item(self):
        if self.boq_item_id:
            self.unit_cost = self.boq_item_id.unit_cost
            self.description = self.boq_item_id.name
