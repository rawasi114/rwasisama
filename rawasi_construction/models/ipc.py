# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiIpc(models.Model):
    """المستخلص الدوري (IPC) — مطالبة مالية بنسب الإنجاز."""

    _name = "rawasi.ipc"
    _description = "مستخلص دوري — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, ipc_number"

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True, default="جديد")
    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    ipc_number = fields.Integer(string="رقم المستخلص", default=1)
    date_from = fields.Date(string="من تاريخ")
    date_to = fields.Date(string="إلى تاريخ", default=fields.Date.context_today)
    line_ids = fields.One2many("rawasi.ipc.line", "ipc_id", string="بنود الإنجاز")

    amount_work = fields.Monetary(
        compute="_compute_amounts", store=True, string="قيمة الأعمال", currency_field="currency_id"
    )
    retention_pct = fields.Float(string="نسبة المحتجز %", default=5.0)
    retention_amount = fields.Monetary(
        compute="_compute_amounts", store=True, string="المحتجز", currency_field="currency_id"
    )
    advance_recovery = fields.Monetary(string="استرداد الدفعة المقدمة", currency_field="currency_id")
    previous_amount = fields.Monetary(string="إجمالي المستخلصات السابقة", currency_field="currency_id")
    net_amount = fields.Monetary(
        compute="_compute_amounts", store=True, string="صافي المستحق", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("paid", "مدفوع"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends(
        "line_ids.amount", "retention_pct", "advance_recovery", "previous_amount"
    )
    def _compute_amounts(self):
        for ipc in self:
            work = sum(ipc.line_ids.mapped("amount"))
            ipc.amount_work = work
            ipc.retention_amount = work * (ipc.retention_pct / 100.0)
            ipc.net_amount = (
                work - ipc.retention_amount - ipc.advance_recovery - ipc.previous_amount
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.ipc") or "جديد"
        return super().create(vals_list)

    def action_submit(self):
        self._require_state(["draft"])
        if not self.line_ids:
            raise UserError("لا يمكن تقديم مستخلص بلا بنود.")
        self.state = "submitted"

    def action_approve(self):
        self._require_state(["submitted"])
        self.state = "approved"

    def action_mark_paid(self):
        self._require_state(["approved"])
        self.state = "paid"

    def action_reset_draft(self):
        self._require_state(["submitted"])
        self.state = "draft"

    def _require_state(self, allowed):
        for ipc in self:
            if ipc.state not in allowed:
                raise UserError("العملية غير مسموحة في الحالة الحالية.")


class RawasiIpcLine(models.Model):
    _name = "rawasi.ipc.line"
    _description = "بند مستخلص — رواسي"
    _order = "ipc_id, sequence, id"

    ipc_id = fields.Many2one(
        "rawasi.ipc", string="المستخلص", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    description = fields.Char(string="البند", required=True)
    uom_id = fields.Many2one("uom.uom", string="الوحدة")
    contract_qty = fields.Float(string="الكمية التعاقدية")
    previous_qty = fields.Float(string="الكمية السابقة")
    current_qty = fields.Float(string="كمية هذا المستخلص")
    cumulative_qty = fields.Float(
        compute="_compute_amounts", store=True, string="الكمية التراكمية"
    )
    unit_price = fields.Monetary(string="سعر الوحدة", currency_field="currency_id")
    amount = fields.Monetary(
        compute="_compute_amounts", store=True, string="القيمة", currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="ipc_id.currency_id", string="العملة")

    @api.depends("previous_qty", "current_qty", "unit_price")
    def _compute_amounts(self):
        for line in self:
            line.cumulative_qty = line.previous_qty + line.current_qty
            line.amount = line.current_qty * line.unit_price

    @api.onchange("boq_item_id")
    def _onchange_boq_item(self):
        if self.boq_item_id:
            self.description = self.boq_item_id.description
            self.uom_id = self.boq_item_id.uom_id.id
            self.contract_qty = self.boq_item_id.qty
            self.unit_price = self.boq_item_id.unit_price
