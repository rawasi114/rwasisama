# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiBoqItem(models.Model):
    _name = "rawasi.boq.item"
    _description = "بند جدول الكميات (النواة الذرية للنظام)"
    _order = "competition_id, sequence, id"

    competition_id = fields.Many2one(
        "rawasi.competition",
        string="المنافسة",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    serial = fields.Char(string="الرقم التسلسلي")
    category = fields.Char(string="الفئة", index=True)
    work_group = fields.Char(string="البند/المجموعة")
    name = fields.Text(string="وصف البند", required=True)
    specifications = fields.Text(string="المواصفات")

    unit_text = fields.Char(string="الوحدة (كما وردت)")
    unit_id = fields.Many2one("rawasi.unit", string="الوحدة")
    quantity = fields.Float(string="الكمية", default=0.0)

    # ── ربط المنتج (النواة الذرية الجديدة) ──────────────────────────
    product_id = fields.Many2one(
        "product.product",
        string="المنتج",
        index=True,
        domain="[('is_construction', '=', True)]",
        help="المنتج الذي يمثّل هذا البند في كتالوج المنتجات الموحَّد. "
             "عند التحديد يصبح المنتج هو النواة المرجعية للشراء/الاستلام/الاستهلاك.",
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        related="product_id.product_tmpl_id",
        store=True,
        string="قالب المنتج",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for item in self:
            product = item.product_id
            if not product:
                continue
            tmpl = product.product_tmpl_id
            if not item.name:
                item.name = tmpl.name
            if tmpl.rawasi_unit_id and not item.unit_id:
                item.unit_id = tmpl.rawasi_unit_id
            if tmpl.sbc_code_id and not item.sbc_code_id:
                item.sbc_code_id = tmpl.sbc_code_id
            if tmpl.specifications and not item.specifications:
                item.specifications = tmpl.specifications

    mandatory_local = fields.Selection(
        [("yes", "نعم"), ("no", "لا")],
        string="منتج من القائمة الإلزامية",
    )
    construction_code = fields.Char(string="الرمز الإنشائي (كما ورد)")
    sbc_code_id = fields.Many2one("rawasi.sbc.code", string="رمز SBC")
    # ── ربط جذري ببنود المرجع (سجل البنود المرجعي) ────────────────
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي",
        index=True, ondelete="set null",
        help="الربط بكتالوج البنود المرجعي الموحَّد لشركة رواسي سما.",
    )
    lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        help="رمز هيئة المحتوى المحلي المرتبط بالبند.",
    )

    currency_id = fields.Many2one(
        related="competition_id.currency_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        "res.company", related="competition_id.company_id", store=True, readonly=True,
    )
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    total_cost = fields.Monetary(
        string="إجمالي التكلفة", compute="_compute_totals", store=True
    )
    unit_price = fields.Monetary(string="سعر الوحدة")
    total_price = fields.Monetary(
        string="إجمالي السعر", compute="_compute_totals", store=True
    )
    margin_pct = fields.Float(
        string="هامش %", compute="_compute_totals", store=True
    )

    @api.depends("quantity", "unit_cost", "unit_price")
    def _compute_totals(self):
        for item in self:
            item.total_cost = item.quantity * item.unit_cost
            item.total_price = item.quantity * item.unit_price
            item.margin_pct = (
                (item.unit_price - item.unit_cost) / item.unit_price * 100.0
                if item.unit_price
                else 0.0
            )

    # ── الميزانية (يُبنى عليها فحص الميزانية الآلي) ──────────────
    is_locked = fields.Boolean(
        string="مقفل للطلبات",
        help="عند التفعيل يُمنع إنشاء طلبات مواد جديدة على هذا البند.",
    )
    mr_line_ids = fields.One2many(
        "rawasi.material.request.line", "boq_item_id", string="سطور طلبات المواد"
    )
    po_line_ids = fields.One2many(
        "rawasi.purchase.order.line", "boq_item_id", string="سطور أوامر الشراء"
    )
    dsr_progress_line_ids = fields.One2many(
        "rawasi.dsr.progress.line", "boq_item_id",
        string="سطور إنجاز DSR",
    )
    qty_executed = fields.Float(
        string="الكمية المنفّذة",
        compute="_compute_qty_executed", store=True,
        help="مجموع الكميات المنفّذة من هذا البند عبر التقارير اليومية المعتمدة.",
    )
    qty_remaining = fields.Float(
        string="الكمية المتبقية",
        compute="_compute_qty_executed", store=True,
    )
    qty_executed_pct = fields.Float(
        string="نسبة الإنجاز %",
        compute="_compute_qty_executed", store=True,
    )

    @api.depends(
        "quantity",
        "dsr_progress_line_ids.qty_today",
        "dsr_progress_line_ids.report_state",
    )
    def _compute_qty_executed(self):
        for item in self:
            done = sum(
                ln.qty_today for ln in item.dsr_progress_line_ids
                if ln.report_state == "confirmed"
            )
            item.qty_executed = done
            item.qty_remaining = max((item.quantity or 0.0) - done, 0.0)
            item.qty_executed_pct = (
                (done / item.quantity * 100.0) if item.quantity else 0.0
            )
    amount_committed = fields.Monetary(
        string="المرتبط (Committed)", compute="_compute_budget", store=True
    )
    amount_spent = fields.Monetary(
        string="المنفَق (Spent)", compute="_compute_budget", store=True
    )
    amount_consumed = fields.Monetary(
        string="المستهلك", compute="_compute_budget", store=True
    )
    amount_remaining = fields.Monetary(
        string="المتبقي", compute="_compute_budget", store=True
    )
    consumption_pct = fields.Float(
        string="نسبة الاستهلاك %", compute="_compute_budget", store=True
    )
    budget_state = fields.Selection(
        [("ok", "ضمن الميزانية"), ("warning", "اقتراب من الحد"), ("over", "تجاوز")],
        string="حالة الميزانية",
        compute="_compute_budget",
        store=True,
    )

    @api.depends(
        "total_cost",
        "mr_line_ids.amount_subtotal",
        "mr_line_ids.request_state",
        "po_line_ids.amount_open",
        "po_line_ids.amount_received",
        "po_line_ids.order_state",
    )
    def _compute_budget(self):
        for item in self:
            committed_mr = sum(
                ln.amount_subtotal
                for ln in item.mr_line_ids
                if ln.request_state == "approved"
            )
            committed_po = sum(
                ln.amount_open
                for ln in item.po_line_ids
                if ln.order_state == "confirmed"
            )
            spent = sum(
                ln.amount_received
                for ln in item.po_line_ids
                if ln.order_state in ("confirmed", "received")
            )
            item.amount_committed = committed_mr + committed_po
            item.amount_spent = spent
            item.amount_consumed = item.amount_committed + spent
            item.amount_remaining = item.total_cost - item.amount_consumed
            item.consumption_pct = (
                (item.amount_consumed / item.total_cost * 100.0)
                if item.total_cost
                else 0.0
            )
            if item.total_cost and item.amount_consumed > item.total_cost:
                item.budget_state = "over"
            elif item.consumption_pct >= 80.0:
                item.budget_state = "warning"
            else:
                item.budget_state = "ok"

    # ── الذكاء التسعيري: اقتراحات من ذاكرة الأسعار ───────────────
    def _price_matches(self, limit=20):
        self.ensure_one()
        return self.env["rawasi.price.intelligence"].search_matches(
            self.name or "",
            unit_id=self.unit_id.id,
            exclude_competition_id=self.competition_id.id,
            limit=limit,
        )

    def action_show_price_suggestions(self):
        """يفتح لوحة الأسعار التاريخية المطابقة لهذا البند (Side Panel)."""
        self.ensure_one()
        matches = self._price_matches()
        match_ids = [rec.id for _score, rec in matches]
        return {
            "type": "ir.actions.act_window",
            "name": _("اقتراحات الأسعار — %s") % (self.name or ""),
            "res_model": "rawasi.price.intelligence",
            "view_mode": "list,form",
            "domain": [("id", "in", match_ids)],
            "context": {"create": False, "edit": False},
        }

    def action_apply_best_price(self):
        """يطبّق أفضل سعر تاريخي مطابق على تكلفة/سعر الوحدة."""
        self.ensure_one()
        matches = self._price_matches(limit=1)
        if not matches:
            raise UserError(_("لا توجد أسعار تاريخية مطابقة لهذا البند."))
        _score, best = matches[0]
        self.unit_cost = best.unit_cost
        self.unit_price = best.unit_price
        return True
