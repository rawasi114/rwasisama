# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiVariationOrder(models.Model):
    _name = "rawasi.variation.order"
    _description = "أمر تغيير (Variation Order)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"

    name = fields.Char(string="الرقم", default="/", readonly=True, copy=False)
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    subject = fields.Char(string="الموضوع", required=True, tracking=True)
    vo_type = fields.Selection(
        [
            ("addition", "إضافة أعمال"),
            ("omission", "حذف أعمال"),
            ("variation", "تعديل (كميات/أسعار)"),
        ],
        string="النوع",
        default="addition",
        required=True,
        tracking=True,
    )
    reason = fields.Text(string="المبرّر")
    vo_date = fields.Date(string="التاريخ", default=fields.Date.context_today, tracking=True)
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("rejected", "مرفوض"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    applied = fields.Boolean(string="طُبّق على جدول الكميات", readonly=True, copy=False)
    line_ids = fields.One2many(
        "rawasi.variation.order.line", "vo_id", string="بنود التغيير"
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount_total = fields.Monetary(
        string="صافي أثر التغيير", compute="_compute_amount_total", store=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "rawasi_vo_attachment_rel", "vo_id", "attachment_id",
        string="المرفقات",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.variation.order"
                ) or "/"
        return super().create(vals_list)

    @api.depends("line_ids.amount_subtotal")
    def _compute_amount_total(self):
        for vo in self:
            vo.amount_total = sum(vo.line_ids.mapped("amount_subtotal"))

    def _report_xmlid(self):
        return "rawasi_construction.action_report_variation_order"

    def _get_competition(self):
        self.ensure_one()
        return self.env["rawasi.competition"].search(
            [("project_id", "=", self.project_id.id)], limit=1
        )

    def action_submit(self):
        for vo in self:
            if not vo.line_ids:
                raise UserError(_("لا يمكن تقديم أمر تغيير بلا بنود."))
            vo.state = "submitted"

    def action_approve(self):
        for vo in self:
            vo._apply_to_boq()
            vo.state = "approved"

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})

    def _apply_to_boq(self):
        """يطبّق تغييرات الكميات/البنود الجديدة على جدول الكميات (مرّة واحدة)."""
        self.ensure_one()
        if self.applied:
            return
        competition = self._get_competition()
        for line in self.line_ids:
            if line.change_type == "new_item":
                if not competition:
                    raise UserError(_(
                        "لا توجد منافسة مرتبطة بالمشروع لإضافة بند جديد."
                    ))
                self.env["rawasi.boq.item"].create({
                    "competition_id": competition.id,
                    "name": line.description or line.name or _("بند أمر تغيير"),
                    "quantity": line.quantity,
                    "unit_cost": line.unit_cost,
                    "unit_price": line.unit_price,
                })
            elif line.boq_item_id:
                if line.change_type == "add_qty":
                    line.boq_item_id.quantity += line.quantity
                elif line.change_type == "omit_qty":
                    line.boq_item_id.quantity = max(
                        0.0, line.boq_item_id.quantity - line.quantity
                    )
        self.applied = True


class RawasiVariationOrderLine(models.Model):
    _name = "rawasi.variation.order.line"
    _description = "سطر أمر تغيير"

    vo_id = fields.Many2one(
        "rawasi.variation.order", required=True, ondelete="cascade"
    )
    change_type = fields.Selection(
        [
            ("add_qty", "زيادة كمية بند"),
            ("omit_qty", "تخفيض كمية بند"),
            ("new_item", "بند جديد"),
        ],
        string="نوع التغيير",
        default="add_qty",
        required=True,
    )
    # رابط بند BOQ المتأثر (إلزامي إلا لبند جديد)
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    name = fields.Char(string="وصف البند الجديد")
    description = fields.Char(string="الوصف")
    quantity = fields.Float(string="الكمية", default=0.0)
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    unit_price = fields.Monetary(string="سعر الوحدة")
    currency_id = fields.Many2one(related="vo_id.currency_id")
    amount_subtotal = fields.Monetary(
        string="الأثر", compute="_compute_subtotal", store=True
    )

    @api.depends("change_type", "quantity", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            value = line.quantity * line.unit_price
            line.amount_subtotal = -value if line.change_type == "omit_qty" else value

    @api.onchange("boq_item_id")
    def _onchange_boq_item(self):
        if self.boq_item_id:
            self.description = self.boq_item_id.name
            self.unit_cost = self.boq_item_id.unit_cost
            self.unit_price = self.boq_item_id.unit_price

    @api.constrains("change_type", "boq_item_id")
    def _check_boq_item(self):
        for line in self:
            if line.change_type in ("add_qty", "omit_qty") and not line.boq_item_id:
                raise UserError(_(
                    "يلزم تحديد بند جدول الكميات لتغييرات الكميات."
                ))
