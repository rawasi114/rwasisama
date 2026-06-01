# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiCompetition(models.Model):
    """المنافسة (المناقصة) — نقطة بداية دورة الأعمال.

    تحمل جدول الكميات (BoQ)؛ وعند الترسية (won) تتحوّل إلى مشروع فعلي مع
    حساب تحليلي ضمن خطة «مشاريع المقاولات».
    """

    _name = "rawasi.competition"
    _description = "منافسة — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "submission_date desc, id desc"

    name = fields.Char(
        string="المرجع",
        required=True,
        copy=False,
        readonly=True,
        default="جديد",
        index=True,
    )
    title = fields.Char(string="اسم المنافسة", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner", string="الجهة / العميل", required=True, tracking=True
    )
    client_reference = fields.Char(string="مرجع الجهة")
    description = fields.Text(string="الوصف")
    submission_date = fields.Date(string="تاريخ التقديم", tracking=True)
    validity_days = fields.Integer(string="مدة سريان العرض (يوم)", default=90)
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("pricing", "قيد التسعير"),
            ("submitted", "مقدَّمة"),
            ("won", "فائزة"),
            ("lost", "خاسرة"),
            ("cancelled", "ملغاة"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
        index=True,
    )
    boq_item_ids = fields.One2many("rawasi.boq.item", "competition_id", string="جدول الكميات")
    boq_count = fields.Integer(compute="_compute_boq_count", string="عدد البنود")
    amount_total = fields.Monetary(
        compute="_compute_amount_total", store=True, string="الإجمالي", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", readonly=True, copy=False
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("boq_item_ids.subtotal")
    def _compute_amount_total(self):
        for comp in self:
            comp.amount_total = sum(comp.boq_item_ids.mapped("subtotal"))

    def _compute_boq_count(self):
        for comp in self:
            comp.boq_count = len(comp.boq_item_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.competition") or "جديد"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # سير الحالة
    # ------------------------------------------------------------------
    def action_set_pricing(self):
        self._require_state(["draft"])
        self.state = "pricing"

    def action_submit(self):
        self._require_state(["pricing"])
        if not self.boq_item_ids:
            raise UserError("لا يمكن تقديم منافسة بلا بنود في جدول الكميات.")
        for comp in self:
            comp._capture_price_intelligence()
        self.state = "submitted"

    def action_won(self):
        self._require_state(["submitted"])
        for comp in self:
            if not comp.project_id:
                comp.project_id = comp._create_project()
            comp._set_price_outcome("won")
            comp.state = "won"
        return True

    def action_lost(self):
        self._require_state(["submitted"])
        for comp in self:
            comp._set_price_outcome("lost")
        self.state = "lost"

    # ------------------------------------------------------------------
    # ذاكرة التسعير
    # ------------------------------------------------------------------
    def _capture_price_intelligence(self):
        """يلتقط بنود جدول الكميات في ذاكرة الأسعار عند التقديم (لا تكرار)."""
        self.ensure_one()
        Price = self.env["rawasi.price.intelligence"]
        Price.search([("competition_id", "=", self.id)]).unlink()
        vals = []
        for line in self.boq_item_ids:
            if not line.unit_price:
                continue
            vals.append(
                {
                    "name": line.description,
                    "competition_id": self.id,
                    "boq_item_id": line.id,
                    "category": line.category,
                    "uom_id": line.uom_id.id,
                    "lcgpa_code_id": line.reference_item_id.lcgpa_code_id.id or False,
                    "sbc_code_id": line.reference_item_id.sbc_code_id.id or False,
                    "quantity": line.qty,
                    "currency_id": self.currency_id.id,
                    "unit_cost": line.unit_cost,
                    "unit_price": line.unit_price,
                    "price_date": self.submission_date or fields.Date.today(),
                    "outcome": "submitted",
                }
            )
        if vals:
            Price.create(vals)

    def _set_price_outcome(self, outcome):
        self.ensure_one()
        self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", self.id)]
        ).write({"outcome": outcome})

    def action_cancel(self):
        self._require_state(["draft", "pricing", "submitted"])
        self.state = "cancelled"

    def action_reset_draft(self):
        self._require_state(["lost", "cancelled"])
        self.state = "draft"

    def _create_project(self):
        """ينشئ مشروعاً بحساب تحليلي ضمن خطة «مشاريع المقاولات»."""
        self.ensure_one()
        plan = self.env.ref("rawasi_base.analytic_plan_construction", raise_if_not_found=False)
        analytic = False
        if plan:
            analytic = self.env["account.analytic.account"].create(
                {"name": self.title, "plan_id": plan.id, "partner_id": self.partner_id.id}
            )
        project = self.env["project.project"].create(
            {
                "name": self.title,
                "partner_id": self.partner_id.id,
                "rawasi_competition_id": self.id,
                "rawasi_is_construction": True,
                "account_id": analytic.id if analytic else False,
            }
        )
        return project.id

    def action_view_project(self):
        self.ensure_one()
        if not self.project_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }

    def _require_state(self, allowed):
        for comp in self:
            if comp.state not in allowed:
                label = dict(comp._fields["state"].selection).get(comp.state, comp.state)
                raise UserError("العملية غير مسموحة في الحالة: %s" % label)


class RawasiBoqItem(models.Model):
    """بند جدول الكميات — مرتبط ببند مرجعي من الكتالوج."""

    _name = "rawasi.boq.item"
    _description = "بند جدول كميات — رواسي"
    _order = "competition_id, sequence, id"

    competition_id = fields.Many2one(
        "rawasi.competition", string="المنافسة", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    serial = fields.Char(string="الرقم التسلسلي")
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي", index=True
    )
    code = fields.Char(string="الرمز")
    category = fields.Char(string="الفئة")
    description = fields.Char(string="البند", required=True)
    specification = fields.Text(string="المواصفات")
    uom_id = fields.Many2one("uom.uom", string="الوحدة", required=True)
    qty = fields.Float(string="الكمية", default=1.0)
    unit_cost = fields.Monetary(string="التكلفة الإفرادي", currency_field="currency_id")
    total_cost = fields.Monetary(
        compute="_compute_total_cost", store=True, string="إجمالي التكلفة للبند",
        currency_field="currency_id",
    )
    unit_price = fields.Monetary(string="السعر الإفرادي", currency_field="currency_id")
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="إجمالي البند", currency_field="currency_id"
    )
    cost_estimate = fields.Monetary(
        related="reference_item_id.standard_cost", string="التكلفة المعيارية",
        currency_field="currency_id",
    )
    procurement_type = fields.Selection(
        related="reference_item_id.procurement_type", string="مسار التوريد", store=True
    )
    product_id = fields.Many2one(
        related="reference_item_id.product_id", string="المنتج", store=True
    )
    currency_id = fields.Many2one(
        related="competition_id.currency_id", string="العملة", store=True
    )

    @api.depends("qty", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_price

    @api.depends("qty", "unit_cost")
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.qty * line.unit_cost

    @api.onchange("reference_item_id")
    def _onchange_reference_item(self):
        if self.reference_item_id:
            ref = self.reference_item_id
            self.code = ref.code
            self.description = ref.name
            self.specification = ref.specification
            self.uom_id = ref.uom_id.id
            if not self.unit_cost:
                self.unit_cost = ref.standard_cost
            if not self.unit_price:
                self.unit_price = ref.standard_cost

    def action_find_similar_prices(self):
        """يفتح أسعاراً تاريخية مشابهة لهذا البند من ذاكرة الأسعار."""
        self.ensure_one()
        matches = self.env["rawasi.price.intelligence"].search_matches(
            self.description,
            uom_id=self.uom_id.id,
            exclude_competition_id=self.competition_id.id,
        )
        match_ids = [rec.id for _score, rec in matches]
        return {
            "type": "ir.actions.act_window",
            "name": "أسعار تاريخية مشابهة",
            "res_model": "rawasi.price.intelligence",
            "view_mode": "list,form",
            "domain": [("id", "in", match_ids)],
            "context": {"create": False},
        }
