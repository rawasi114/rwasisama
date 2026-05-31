# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiWorkshopMo(models.Model):
    """أمر تصنيع الورشة مع بوابات الدفع.

    بوابات الدفع للعميل الخارجي:
      * بدء التصنيع يتطلب دفعة ≥ 50%.
      * التسليم يتطلب سداد ≥ 100%.
    للتصنيع الداخلي (is_internal) تُتجاوز البوابات (no_payment_required).
    منطق التكامل (إنشاء MO داخلي، النقل التلقائي للمشروع) يضيفه موديول
    المقاولات في المرحلة 7 دون تعديل هذا النموذج جوهرياً.
    """

    _name = "rawasi.workshop.mo"
    _description = "أمر تصنيع ورشة — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="المرجع", default="جديد", readonly=True, copy=False, index=True)
    section_id = fields.Many2one(
        "rawasi.workshop.section", string="القسم", required=True, tracking=True, index=True
    )
    partner_id = fields.Many2one("res.partner", string="العميل", tracking=True)
    sale_order_id = fields.Many2one("sale.order", string="أمر البيع", readonly=True, copy=False)
    date_order = fields.Datetime(string="تاريخ الأمر", default=fields.Datetime.now)
    date_deadline = fields.Date(string="تاريخ التسليم المطلوب")
    product_line_ids = fields.One2many(
        "rawasi.workshop.mo.line", "mo_id", string="المنتجات"
    )
    note = fields.Text(string="ملاحظات")

    amount_total = fields.Monetary(
        compute="_compute_amount_total", store=True, string="القيمة الإجمالية",
        currency_field="currency_id",
    )
    amount_received = fields.Monetary(string="المسدَّد", tracking=True, currency_field="currency_id")
    deposit_pct = fields.Float(
        compute="_compute_deposit_pct", store=True, string="نسبة السداد %"
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )

    # ⭐ نقاط امتداد التكامل (تُضبط من موديول المقاولات في المرحلة 7)
    is_internal = fields.Boolean(
        string="تصنيع داخلي", default=False,
        help="إن كان الأمر ناتجاً عن تصنيع داخلي لمشروع مقاولات (تُتجاوز بوابات الدفع).",
    )
    no_payment_required = fields.Boolean(
        compute="_compute_gates", store=True, string="بلا بوابة دفع"
    )
    can_start_production = fields.Boolean(compute="_compute_gates", store=True)
    can_start_delivery = fields.Boolean(compute="_compute_gates", store=True)

    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("confirmed", "مؤكد"),
            ("in_production", "قيد التصنيع"),
            ("done", "اكتمل التصنيع"),
            ("delivered", "سُلِّم"),
            ("cancelled", "ملغى"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("product_line_ids.subtotal")
    def _compute_amount_total(self):
        for mo in self:
            mo.amount_total = sum(mo.product_line_ids.mapped("subtotal"))

    @api.depends("amount_received", "amount_total")
    def _compute_deposit_pct(self):
        for mo in self:
            mo.deposit_pct = (mo.amount_received / mo.amount_total * 100.0) if mo.amount_total else 0.0

    @api.depends("is_internal", "deposit_pct")
    def _compute_gates(self):
        for mo in self:
            mo.no_payment_required = mo.is_internal
            mo.can_start_production = mo.no_payment_required or mo.deposit_pct >= 50.0
            mo.can_start_delivery = mo.no_payment_required or mo.deposit_pct >= 100.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.workshop.mo") or "جديد"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # سير الحالة + بوابات الدفع
    # ------------------------------------------------------------------
    def action_confirm(self):
        self._require_state(["draft"])
        if not self.product_line_ids:
            raise UserError("لا يمكن تأكيد أمر تصنيع بلا منتجات.")
        self.write({"state": "confirmed"})
        self._notify("mo_confirmed")

    def action_start_production(self):
        self._require_state(["confirmed"])
        for mo in self:
            if not mo.can_start_production:
                raise UserError(
                    "لا يمكن بدء التصنيع قبل سداد دفعة 50%% على الأقل (الحالي %.0f%%)."
                    % mo.deposit_pct
                )
        self.write({"state": "in_production"})
        self._notify("mo_in_production")

    def action_done(self):
        self._require_state(["in_production"])
        self.write({"state": "done"})
        self._notify("mo_done")

    def action_deliver(self):
        self._require_state(["done"])
        for mo in self:
            if not mo.can_start_delivery:
                raise UserError(
                    "لا يمكن التسليم قبل سداد كامل القيمة (الحالي %.0f%%)." % mo.deposit_pct
                )
        self.write({"state": "delivered"})
        self._notify("mo_delivered")

    def action_cancel(self):
        self._require_state(["draft", "confirmed", "in_production"])
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self._require_state(["cancelled"])
        self.write({"state": "draft"})

    def _notify(self, event):
        self.env["rawasi.notification.hook"].send(self, event)

    def _require_state(self, allowed):
        for mo in self:
            if mo.state not in allowed:
                label = dict(mo._fields["state"].selection).get(mo.state, mo.state)
                raise UserError("العملية غير مسموحة في الحالة: %s" % label)


class RawasiWorkshopMoLine(models.Model):
    _name = "rawasi.workshop.mo.line"
    _description = "منتج أمر تصنيع — رواسي"
    _order = "mo_id, sequence, id"

    mo_id = fields.Many2one(
        "rawasi.workshop.mo", string="أمر التصنيع", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    product_id = fields.Many2one("product.product", string="المنتج", required=True)
    description = fields.Char(string="الوصف")
    qty = fields.Float(string="الكمية", default=1.0, required=True)
    qty_produced = fields.Float(string="المُنتَج")
    uom_id = fields.Many2one("uom.uom", string="الوحدة", required=True)
    unit_price = fields.Monetary(string="سعر الوحدة", currency_field="currency_id")
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="الإجمالي", currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="mo_id.currency_id", string="العملة")

    @api.depends("qty", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_price

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.list_price
