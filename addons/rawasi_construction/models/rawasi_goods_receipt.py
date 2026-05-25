# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiGoodsReceipt(models.Model):
    _name = "rawasi.goods.receipt"
    _description = "سند استلام مواد (GRN)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="الرقم", required=True, copy=False, readonly=True, default="/")
    order_id = fields.Many2one(
        "rawasi.purchase.order", string="أمر الشراء", required=True, ondelete="cascade"
    )
    project_id = fields.Many2one(related="order_id.project_id", store=True, string="المشروع")
    receipt_date = fields.Date(string="تاريخ الاستلام", default=fields.Date.context_today)
    state = fields.Selection(
        [("draft", "مسودة"), ("done", "مؤكَّد"), ("cancelled", "ملغى")],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many("rawasi.goods.receipt.line", "receipt_id", string="السطور")
    company_id = fields.Many2one(related="order_id.company_id", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id")
    note = fields.Text(string="ملاحظات")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.goods.receipt"
                ) or "/"
        return super().create(vals_list)

    def action_validate(self):
        for grn in self:
            if not grn.line_ids:
                raise UserError(_("لا يمكن تأكيد سند استلام بلا سطور."))
            grn.state = "done"
            # تحديث حالة أمر الشراء إذا اكتمل الاستلام
            po = grn.order_id
            if all(
                line.qty_received >= line.quantity for line in po.line_ids
            ):
                po.state = "received"

    def action_cancel(self):
        self.write({"state": "cancelled"})


class RawasiGoodsReceiptLine(models.Model):
    _name = "rawasi.goods.receipt.line"
    _description = "سطر سند استلام"

    receipt_id = fields.Many2one(
        "rawasi.goods.receipt", required=True, ondelete="cascade"
    )
    po_line_id = fields.Many2one(
        "rawasi.purchase.order.line", string="سطر أمر الشراء", required=True
    )
    boq_item_id = fields.Many2one(
        related="po_line_id.boq_item_id", store=True, string="بند جدول الكميات"
    )
    description = fields.Char(related="po_line_id.description", string="الوصف")
    quantity = fields.Float(string="الكمية المستلَمة", default=0.0)
    unit_id = fields.Many2one(related="po_line_id.unit_id", string="الوحدة")
