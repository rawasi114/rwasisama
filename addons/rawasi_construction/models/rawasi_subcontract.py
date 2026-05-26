# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiSubcontract(models.Model):
    _name = "rawasi.subcontract"
    _description = "عقد مقاول من الباطن"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"
    _rec_names_search = ["name"]

    name = fields.Char(string="الرقم", default="/", readonly=True, copy=False)
    subcontractor_id = fields.Many2one(
        "rawasi.subcontractor", string="المقاول", required=True, tracking=True
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True,
        index=True,
    )
    contract_date = fields.Date(
        string="تاريخ العقد", default=fields.Date.context_today, tracking=True
    )
    scope = fields.Text(string="نطاق العمل")
    line_ids = fields.One2many(
        "rawasi.subcontract.line", "subcontract_id", string="بنود العقد"
    )
    retention_percent = fields.Float(string="نسبة المحتجز %", default=10.0)
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("active", "نافذ"),
            ("closed", "مغلق"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    total_amount = fields.Monetary(
        string="إجمالي قيمة العقد", compute="_compute_total", store=True
    )
    ipc_ids = fields.One2many(
        "rawasi.subcontract.ipc", "subcontract_id", string="المستخلصات"
    )
    ipc_count = fields.Integer(compute="_compute_ipc_count", string="عدد المستخلصات")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_subcontract_attachment_rel",
        "subcontract_id", "attachment_id",
        string="مرفقات العقد",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.subcontract"
                ) or "/"
        return super().create(vals_list)

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for c in self:
            c.total_amount = sum(c.line_ids.mapped("subtotal"))

    def _compute_ipc_count(self):
        for c in self:
            c.ipc_count = len(c.ipc_ids)

    def _report_xmlid(self):
        return "rawasi_construction.action_report_subcontract"

    # ── سير العمل ────────────────────────────────────────────────
    def action_activate(self):
        for c in self:
            if not c.line_ids:
                raise UserError(_("لا يمكن تفعيل عقد بلا بنود."))
            c.state = "active"

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})

    def action_open_ipcs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("مستخلصات العقد"),
            "res_model": "rawasi.subcontract.ipc",
            "view_mode": "list,form",
            "domain": [("subcontract_id", "=", self.id)],
            "context": {"default_subcontract_id": self.id},
        }


class RawasiSubcontractLine(models.Model):
    _name = "rawasi.subcontract.line"
    _description = "بند عقد مقاول من الباطن"

    subcontract_id = fields.Many2one(
        "rawasi.subcontract", required=True, ondelete="cascade", index=True
    )
    # القيد المعماري: كل بند مرتبط ببند جدول الكميات
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند جدول الكميات", required=True
    )
    description = fields.Char(string="الوصف")
    uom_id = fields.Many2one(related="boq_item_id.unit_id", string="الوحدة")
    quantity = fields.Float(string="الكمية", default=0.0)
    unit_price = fields.Monetary(string="سعر الوحدة")
    currency_id = fields.Many2one(related="subcontract_id.currency_id")
    subtotal = fields.Monetary(
        string="الإجمالي", compute="_compute_subtotal", store=True
    )
    certified_quantity = fields.Float(
        string="الكمية المعتمدة (تراكمي)", compute="_compute_certified"
    )

    @api.onchange("boq_item_id")
    def _onchange_boq_item(self):
        if self.boq_item_id:
            self.description = self.boq_item_id.name
            if not self.unit_price:
                self.unit_price = self.boq_item_id.unit_cost

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for ln in self:
            ln.subtotal = ln.quantity * ln.unit_price

    def _compute_certified(self):
        IpcLine = self.env["rawasi.subcontract.ipc.line"]
        for ln in self:
            if not ln.id:
                ln.certified_quantity = 0.0
                continue
            done = IpcLine.search([
                ("subcontract_line_id", "=", ln.id),
                ("ipc_id.state", "in", ("approved", "paid")),
            ])
            ln.certified_quantity = sum(done.mapped("period_quantity"))
