# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .arabic_utils import normalize_match


class RawasiCompetition(models.Model):
    _name = "rawasi.competition"
    _description = "منافسة / فرصة"
    _inherit = ["mail.thread", "mail.activity.mixin", "rawasi.workflow.mixin"]
    _order = "create_date desc"
    _rec_names_search = ["name", "serial", "reference"]

    name = fields.Char(string="اسم المنافسة", required=True, tracking=True)
    serial = fields.Char(
        string="الرقم التسلسلي", readonly=True, copy=False, index=True,
        help="رقم تسلسلي تلقائي بصيغة RS-TND-YYYY#### يربط المنافسة بكل تفاصيلها.",
    )
    reference = fields.Char(string="الرقم المرجعي (اعتماد)", tracking=True, copy=False)
    entity_name = fields.Char(string="الجهة المالكة", tracking=True)
    description = fields.Text(string="الوصف")
    submission_deadline = fields.Datetime(string="موعد التقديم", tracking=True)

    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("pricing", "قيد التسعير"),
            ("submitted", "مقدَّم"),
            ("won", "فائز"),
            ("lost", "خاسر"),
        ],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="العملة",
        default=lambda self: self._default_currency(),
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("serial"):
                vals["serial"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.competition.serial"
                ) or False
        return super().create(vals_list)

    @api.depends("name", "serial")
    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            if rec.serial:
                rec.display_name = "[%s] %s" % (rec.serial, rec.display_name)

    @api.model
    def _default_currency(self):
        # العملة الافتراضية: الريال السعودي إن وُجد، وإلا عملة الشركة.
        sar = self.env.ref("base.SAR", raise_if_not_found=False)
        return sar or self.env.company.currency_id

    boq_item_ids = fields.One2many(
        "rawasi.boq.item", "competition_id", string="بنود جدول الكميات"
    )
    indirect_cost_ids = fields.One2many(
        "rawasi.indirect.cost", "competition_id", string="التكاليف غير المباشرة"
    )
    price_intelligence_ids = fields.One2many(
        "rawasi.price.intelligence", "competition_id", string="لقطات ذاكرة الأسعار"
    )

    default_margin_pct = fields.Float(
        string="هامش الربح الافتراضي %",
        default=15.0,
        help="يُطبَّق على بنود جدول الكميات عند الضغط على «تطبيق الهامش».",
    )

    boq_item_count = fields.Integer(
        string="عدد البنود", compute="_compute_boq_item_count"
    )
    amount_direct_cost = fields.Monetary(
        string="التكلفة المباشرة", compute="_compute_amounts", store=True
    )
    amount_indirect_cost = fields.Monetary(
        string="التكاليف غير المباشرة", compute="_compute_amounts", store=True
    )
    amount_total_cost = fields.Monetary(
        string="إجمالي التكلفة", compute="_compute_amounts", store=True
    )
    amount_total_price = fields.Monetary(
        string="المبلغ الإجمالي بدون الضريبة", compute="_compute_amounts", store=True
    )
    vat_rate = fields.Float(
        string="نسبة ضريبة القيمة المضافة %",
        default=15.0,
        help="ضريبة القيمة المضافة في السعودية (15%).",
    )
    amount_tax = fields.Monetary(
        string="مبلغ الضريبة", compute="_compute_amounts", store=True
    )
    amount_total_incl_tax = fields.Monetary(
        string="الإجمالي شامل الضريبة", compute="_compute_amounts", store=True
    )
    margin_amount = fields.Monetary(
        string="هامش الربح (قيمة)", compute="_compute_amounts", store=True
    )
    margin_pct = fields.Float(
        string="هامش الربح %", compute="_compute_amounts", store=True
    )

    project_id = fields.Many2one(
        "project.project", string="المشروع", readonly=True, copy=False
    )

    # نتيجة الترسية — تُملأ عند إغلاق المنافسة (فائز/خاسر) لبناء ذاكرة الترسيات.
    award_value = fields.Monetary(
        string="قيمة الترسية",
        tracking=True,
        help="القيمة التي تمت بها الترسية فعلياً (سواء فزنا نحن أو فاز غيرنا). "
             "إلزامية عند الإغلاق كخاسرة لجمع أسعار الترسيات للتحليل.",
    )
    awarded_to = fields.Char(
        string="رست على", tracking=True,
        help="اسم الجهة/المقاول الذي رست عليه المنافسة (في حال خسرناها).",
    )

    @api.depends("boq_item_ids")
    def _compute_boq_item_count(self):
        for comp in self:
            comp.boq_item_count = len(comp.boq_item_ids)

    @api.depends(
        "boq_item_ids.total_cost",
        "boq_item_ids.total_price",
        "indirect_cost_ids.amount",
        "vat_rate",
    )
    def _compute_amounts(self):
        for comp in self:
            direct = sum(comp.boq_item_ids.mapped("total_cost"))
            indirect = sum(comp.indirect_cost_ids.mapped("amount"))
            price = sum(comp.boq_item_ids.mapped("total_price"))
            total_cost = direct + indirect
            comp.amount_direct_cost = direct
            comp.amount_indirect_cost = indirect
            comp.amount_total_cost = total_cost
            comp.amount_total_price = price
            comp.amount_tax = price * (comp.vat_rate / 100.0)
            comp.amount_total_incl_tax = price + comp.amount_tax
            comp.margin_amount = price - total_cost
            comp.margin_pct = (comp.margin_amount / price * 100.0) if price else 0.0

    # ── أزرار سير العمل ──────────────────────────────────────────
    def action_start_pricing(self):
        self.write({"state": "pricing"})

    def action_submit(self):
        for comp in self:
            if not comp.boq_item_ids:
                raise UserError(_("لا يمكن تقديم منافسة بدون بنود جدول كميات."))
        self.write({"state": "submitted"})
        # حفظ الأسعار في ذاكرة المؤسسة تلقائياً عند التقديم
        self._snapshot_prices()

    def action_won(self):
        for comp in self:
            # عند الفوز: قيمة الترسية = إجمالي عرضنا شامل الضريبة (إن لم تكن مُحدَّدة)
            if not comp.award_value:
                comp.award_value = comp.amount_total_incl_tax
        self.write({"state": "won"})
        self.price_intelligence_ids.sudo().write({"outcome": "won"})

    def action_lost(self):
        for comp in self:
            if not comp.award_value or comp.award_value <= 0:
                raise UserError(_(
                    "لإغلاق المنافسة كخاسرة يجب إدخال «قيمة الترسية» أولاً "
                    "(القيمة التي رست بها على الفائز). الهدف بناء ذاكرة "
                    "ترسيات للتحليل المستقبلي."
                ))
        self.write({"state": "lost"})
        self.price_intelligence_ids.sudo().write({"outcome": "lost"})

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.price_intelligence_ids.sudo().unlink()
        self.write({"state": "draft"})

    def _snapshot_prices(self):
        """يلتقط أسعار البنود المسعّرة في ذاكرة الأسعار (تحديث لقطة المنافسة)."""
        PI = self.env["rawasi.price.intelligence"].sudo()
        today = fields.Date.context_today(self)
        for comp in self:
            comp.price_intelligence_ids.sudo().unlink()
            rows = []
            for item in comp.boq_item_ids:
                if not item.unit_price:
                    continue
                rows.append({
                    "competition_id": comp.id,
                    "boq_item_id": item.id,
                    "name": item.name,
                    "name_normalized": normalize_match(item.name),
                    "category": item.category,
                    "unit_id": item.unit_id.id,
                    "unit_text": item.unit_text,
                    "sbc_code_id": item.sbc_code_id.id,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                    "unit_price": item.unit_price,
                    "margin_pct": item.margin_pct,
                    "price_date": today,
                    "currency_id": comp.currency_id.id,
                    "company_id": comp.company_id.id,
                    "outcome": "submitted",
                })
            if rows:
                PI.create(rows)

    def action_apply_margin(self):
        """يطبّق هامش الربح الافتراضي على كل البنود: سعر الوحدة = التكلفة × (1+هامش)."""
        for comp in self:
            factor = 1.0 + (comp.default_margin_pct / 100.0)
            for item in comp.boq_item_ids:
                item.unit_price = item.unit_cost * factor
        return True

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("استيراد جدول الكميات"),
            "res_model": "rawasi.boq.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_competition_id": self.id},
        }

    def action_convert_to_project(self):
        self.ensure_one()
        if self.state != "won":
            raise UserError(_("لا يمكن التحويل لمشروع إلا بعد ترسية المنافسة (فائز)."))
        if self.project_id:
            raise UserError(_("تم تحويل هذه المنافسة لمشروع مسبقاً."))
        project = self.env["project.project"].create(
            {
                "name": self.name,
                "company_id": self.company_id.id,
                "rawasi_is_construction": True,
                "rawasi_competition_id": self.id,
            }
        )
        self.project_id = project.id
        # توليد المراحل الخمس (WBS) تلقائياً للمشروع الجديد
        project.action_generate_wbs_phases()
        self.message_post(body=_("تم تحويل المنافسة إلى مشروع: %s") % project.name)
        return self.action_open_project()

    def action_open_project(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("لا يوجد مشروع مرتبط."))
        return {
            "type": "ir.actions.act_window",
            "name": _("المشروع"),
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }
