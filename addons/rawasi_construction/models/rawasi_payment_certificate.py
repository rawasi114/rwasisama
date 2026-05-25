# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiPaymentCertificate(models.Model):
    _name = "rawasi.payment.certificate"
    _description = "مستخلص دفع (Interim Payment Certificate)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"

    name = fields.Char(string="الرقم", default="/", readonly=True, copy=False)
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    sequence_no = fields.Integer(string="رقم المستخلص", default=1)
    period_from = fields.Date(string="من تاريخ")
    period_to = fields.Date(
        string="إلى تاريخ", default=fields.Date.context_today
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("paid", "مدفوع"),
            ("rejected", "مرفوض"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "rawasi.payment.certificate.line", "pc_id", string="بنود المستخلص"
    )
    retention_pct = fields.Float(string="نسبة محتجز الضمان %", default=10.0)
    advance_recovery = fields.Monetary(string="استرداد الدفعة المقدمة", default=0.0)
    vat_rate = fields.Float(string="ضريبة القيمة المضافة %", default=15.0)

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    amount_work_period = fields.Monetary(
        string="قيمة أعمال الفترة", compute="_compute_amounts", store=True
    )
    amount_cumulative = fields.Monetary(
        string="القيمة التراكمية", compute="_compute_amounts", store=True
    )
    retention_amount = fields.Monetary(
        string="محتجز الضمان", compute="_compute_amounts", store=True
    )
    amount_net = fields.Monetary(
        string="الصافي قبل الضريبة", compute="_compute_amounts", store=True
    )
    amount_tax = fields.Monetary(
        string="الضريبة", compute="_compute_amounts", store=True
    )
    amount_total = fields.Monetary(
        string="الإجمالي المستحق", compute="_compute_amounts", store=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "rawasi_pc_attachment_rel", "pc_id", "attachment_id",
        string="المرفقات",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.payment.certificate"
                ) or "/"
        return super().create(vals_list)

    @api.depends(
        "line_ids.amount_work", "line_ids.amount_cumulative",
        "retention_pct", "advance_recovery", "vat_rate",
    )
    def _compute_amounts(self):
        for pc in self:
            work = sum(pc.line_ids.mapped("amount_work"))
            pc.amount_work_period = work
            pc.amount_cumulative = sum(pc.line_ids.mapped("amount_cumulative"))
            pc.retention_amount = work * (pc.retention_pct / 100.0)
            net = work - pc.retention_amount - pc.advance_recovery
            pc.amount_net = net
            pc.amount_tax = net * (pc.vat_rate / 100.0)
            pc.amount_total = net + pc.amount_tax

    def _report_xmlid(self):
        return "rawasi_construction.action_report_payment_certificate"

    def action_generate_lines(self):
        """ينشئ سطور المستخلص من بنود المشروع، ويحسب الكمية السابقة من المستخلصات المعتمدة."""
        self.ensure_one()
        competition = self.env["rawasi.competition"].search(
            [("project_id", "=", self.project_id.id)], limit=1
        )
        if not competition:
            raise UserError(_("لا توجد منافسة/جدول كميات مرتبط بالمشروع."))
        Line = self.env["rawasi.payment.certificate.line"]
        self.line_ids.unlink()
        rows = []
        for item in competition.boq_item_ids:
            prev_lines = Line.search([
                ("pc_id.project_id", "=", self.project_id.id),
                ("boq_item_id", "=", item.id),
                ("pc_id.state", "in", ("approved", "paid")),
                ("pc_id", "!=", self.id),
            ])
            prev_qty = sum(prev_lines.mapped("work_qty"))
            rows.append({
                "pc_id": self.id,
                "boq_item_id": item.id,
                "contract_qty": item.quantity,
                "unit_price": item.unit_price,
                "prev_qty": prev_qty,
            })
        Line.create(rows)
        return True

    def action_submit(self):
        for pc in self:
            if not pc.line_ids:
                raise UserError(_("لا يمكن تقديم مستخلص بلا بنود."))
            pc.state = "submitted"

    def action_approve(self):
        self.write({"state": "approved"})

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})


class RawasiPaymentCertificateLine(models.Model):
    _name = "rawasi.payment.certificate.line"
    _description = "سطر مستخلص دفع"
    _order = "id"

    pc_id = fields.Many2one(
        "rawasi.payment.certificate", required=True, ondelete="cascade"
    )
    pc_state = fields.Selection(related="pc_id.state", store=True)
    # القيد المعماري: كل سطر مستخلص يرتبط ببند جدول الكميات
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند جدول الكميات", required=True
    )
    description = fields.Text(related="boq_item_id.name", string="الوصف")
    unit_id = fields.Many2one(related="boq_item_id.unit_id", string="الوحدة")
    contract_qty = fields.Float(string="الكمية التعاقدية")
    unit_price = fields.Monetary(string="سعر الوحدة")
    prev_qty = fields.Float(string="الكمية السابقة")
    work_qty = fields.Float(string="كمية الفترة", default=0.0)
    cumulative_qty = fields.Float(
        string="الكمية التراكمية", compute="_compute_line", store=True
    )
    cumulative_pct = fields.Float(
        string="نسبة الإنجاز %", compute="_compute_line", store=True
    )
    amount_work = fields.Monetary(
        string="قيمة الفترة", compute="_compute_line", store=True
    )
    amount_cumulative = fields.Monetary(
        string="القيمة التراكمية", compute="_compute_line", store=True
    )
    currency_id = fields.Many2one(related="pc_id.currency_id")

    @api.depends("prev_qty", "work_qty", "unit_price", "contract_qty")
    def _compute_line(self):
        for line in self:
            cumulative = line.prev_qty + line.work_qty
            line.cumulative_qty = cumulative
            line.amount_work = line.work_qty * line.unit_price
            line.amount_cumulative = cumulative * line.unit_price
            line.cumulative_pct = (
                (cumulative / line.contract_qty * 100.0) if line.contract_qty else 0.0
            )

    @api.constrains("work_qty", "prev_qty", "contract_qty")
    def _check_overrun(self):
        for line in self:
            if line.contract_qty and (line.prev_qty + line.work_qty) > line.contract_qty:
                raise UserError(_(
                    "الكمية التراكمية للبند «%s» تتجاوز الكمية التعاقدية."
                ) % (line.boq_item_id.name or ""))
