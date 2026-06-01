# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RawasiSubcontractIpc(models.Model):
    _name = "rawasi.subcontract.ipc"
    _description = "مستخلص مقاول من الباطن"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"
    _rec_names_search = ["name"]

    name = fields.Char(string="الرقم", default="/", readonly=True, copy=False)
    subcontract_id = fields.Many2one(
        "rawasi.subcontract", string="العقد", required=True, tracking=True,
        index=True,
    )
    project_id = fields.Many2one(
        related="subcontract_id.project_id", store=True, index=True,
        string="المشروع",
    )
    subcontractor_id = fields.Many2one(
        related="subcontract_id.subcontractor_id", store=True, string="المقاول"
    )
    ipc_date = fields.Date(
        string="تاريخ المستخلص", default=fields.Date.context_today, tracking=True
    )
    line_ids = fields.One2many(
        "rawasi.subcontract.ipc.line", "ipc_id", string="بنود المستخلص"
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("approved", "معتمد"),
            ("paid", "مدفوع"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    payment_date = fields.Date(string="تاريخ الدفع")
    payment_reference = fields.Char(string="مرجع سند الصرف")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")

    subtotal = fields.Monetary(
        string="قيمة الفترة", compute="_compute_amounts", store=True
    )
    retention_amount = fields.Monetary(
        string="المحتجز", compute="_compute_amounts", store=True
    )
    other_deductions = fields.Monetary(string="خصومات أخرى", default=0.0)
    net_before_vat = fields.Monetary(
        string="الصافي قبل الضريبة", compute="_compute_amounts", store=True
    )
    vat_rate = fields.Float(string="نسبة الضريبة %", default=15.0)
    vat_amount = fields.Monetary(
        string="الضريبة", compute="_compute_amounts", store=True
    )
    net_payable = fields.Monetary(
        string="الصافي المستحق", compute="_compute_amounts", store=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_subcontract_ipc_attachment_rel",
        "ipc_id", "attachment_id",
        string="المرفقات",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.subcontract.ipc"
                ) or "/"
        return super().create(vals_list)

    @api.depends(
        "line_ids.period_value",
        "other_deductions",
        "subcontract_id.retention_percent",
        "vat_rate",
    )
    def _compute_amounts(self):
        for r in self:
            subtotal = sum(r.line_ids.mapped("period_value"))
            ret_pct = r.subcontract_id.retention_percent or 0.0
            retention = subtotal * (ret_pct / 100.0)
            net = subtotal - retention - r.other_deductions
            vat = net * (r.vat_rate / 100.0)
            r.subtotal = subtotal
            r.retention_amount = retention
            r.net_before_vat = net
            r.vat_amount = vat
            r.net_payable = net + vat

    def _report_xmlid(self):
        return "rawasi_construction.action_report_subcontract_ipc"

    def action_generate_lines(self):
        """يولّد سطور المستخلص من بنود العقد (مرة واحدة، فارغة)."""
        self.ensure_one()
        if not self.subcontract_id:
            raise UserError(_("اختر العقد أولاً."))
        Line = self.env["rawasi.subcontract.ipc.line"]
        self.line_ids.unlink()
        rows = []
        for cl in self.subcontract_id.line_ids:
            rows.append({
                "ipc_id": self.id,
                "subcontract_line_id": cl.id,
            })
        if rows:
            Line.create(rows)
        return True

    def action_approve(self):
        self._ensure_tech_approver()
        for r in self:
            # تحقق إلزامي: التراكمي لا يتجاوز التعاقدي
            for ln in r.line_ids:
                if ln.contract_quantity and ln.cumulative_quantity > ln.contract_quantity + 0.0001:
                    raise UserError(_(
                        "الكمية التراكمية للبند «%s» (%s) تتجاوز الكمية التعاقدية (%s)."
                    ) % (
                        ln.description or "", ln.cumulative_quantity, ln.contract_quantity,
                    ))
        self.write({"state": "approved"})

    def action_mark_paid(self):
        self._ensure_finance_user()
        for r in self:
            r.state = "paid"
            if not r.payment_date:
                r.payment_date = fields.Date.context_today(r)

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})


class RawasiSubcontractIpcLine(models.Model):
    _name = "rawasi.subcontract.ipc.line"
    _description = "بند مستخلص مقاول من الباطن"

    ipc_id = fields.Many2one(
        "rawasi.subcontract.ipc", required=True, ondelete="cascade", index=True
    )
    ipc_state = fields.Selection(related="ipc_id.state", store=True)
    subcontract_line_id = fields.Many2one(
        "rawasi.subcontract.line", string="بند العقد", required=True, index=True
    )
    description = fields.Char(related="subcontract_line_id.description", string="الوصف")
    uom_id = fields.Many2one(related="subcontract_line_id.uom_id", string="الوحدة")
    contract_quantity = fields.Float(
        related="subcontract_line_id.quantity", string="الكمية التعاقدية"
    )
    unit_price = fields.Monetary(
        related="subcontract_line_id.unit_price", string="سعر الوحدة"
    )
    previous_quantity = fields.Float(
        string="الكمية السابقة", compute="_compute_previous_quantity",
    )
    period_quantity = fields.Float(string="كمية الفترة", default=0.0)
    cumulative_quantity = fields.Float(
        string="الكمية التراكمية", compute="_compute_cumulative", store=True,
    )
    progress_percent = fields.Float(
        string="نسبة الإنجاز %", compute="_compute_cumulative", store=True,
    )
    period_value = fields.Monetary(
        string="قيمة الفترة", compute="_compute_value", store=True
    )
    currency_id = fields.Many2one(related="ipc_id.currency_id")

    @api.depends("subcontract_line_id")
    def _compute_previous_quantity(self):
        """الكمية السابقة محسوبة من المستخلصات المعتمدة الأخرى (غير مخزّنة)."""
        IpcLine = self.env["rawasi.subcontract.ipc.line"]
        for ln in self:
            domain = [
                ("subcontract_line_id", "=", ln.subcontract_line_id.id),
                ("ipc_id.state", "in", ("approved", "paid")),
            ]
            if ln.id:
                domain.append(("id", "!=", ln.id))
            ln.previous_quantity = sum(IpcLine.search(domain).mapped("period_quantity"))

    @api.depends("previous_quantity", "period_quantity", "contract_quantity")
    def _compute_cumulative(self):
        """الكمية التراكمية ونسبة الإنجاز (مخزّنتان، تعتمدان على الكمية السابقة + الفترة)."""
        for ln in self:
            ln.cumulative_quantity = ln.previous_quantity + ln.period_quantity
            ln.progress_percent = (
                (ln.cumulative_quantity / ln.contract_quantity * 100.0)
                if ln.contract_quantity else 0.0
            )

    @api.depends("period_quantity", "unit_price")
    def _compute_value(self):
        for ln in self:
            ln.period_value = ln.period_quantity * ln.unit_price

    @api.constrains("period_quantity", "contract_quantity")
    def _check_overrun(self):
        for ln in self:
            if ln.contract_quantity and (ln.previous_quantity + ln.period_quantity) > ln.contract_quantity + 0.0001:
                raise ValidationError(_(
                    "الكمية التراكمية للبند «%s» تتجاوز الكمية التعاقدية."
                ) % (ln.description or ""))
