# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RawasiEosSettlement(models.Model):
    """تسوية مكافأة نهاية الخدمة وفق نظام العمل السعودي.

    قاعدة الاحتساب (المادة 84):
      - نصف شهر عن كل سنة من السنوات الخمس الأولى.
      - شهر كامل عن كل سنة من السنوات التالية.
      - تُحسب أجزاء السنة بالتناسب، على أساس الأجر الأخير.

    نِسَب الاستحقاق عند الاستقالة (المادة 85):
      - الخدمة أقل من سنتين: لا يستحق شيئاً.
      - من سنتين إلى أقل من خمس: ثلث المكافأة.
      - من خمس إلى أقل من عشر: ثلثا المكافأة.
      - عشر سنوات فأكثر: المكافأة كاملة.

    حالات استحقاق المكافأة كاملةً رغم كونها بمبادرة العامل (المادة 87
    والحالات المماثلة): الوفاة/العجز، إنهاء صاحب العمل، انتهاء العقد محدد
    المدة، الحالات الخاصة (زواج/وضع المرأة، القوة القاهرة).
    """

    _name = "rawasi.eos.settlement"
    _description = "تسوية نهاية الخدمة"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "end_date desc, id desc"

    name = fields.Char(
        string="المرجع",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("جديد"),
    )
    employee_id = fields.Many2one(
        "hr.employee", string="الموظف", required=True, tracking=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )

    start_date = fields.Date(string="تاريخ المباشرة", required=True, tracking=True)
    end_date = fields.Date(string="تاريخ انتهاء الخدمة", required=True, tracking=True)

    reason = fields.Selection(
        selection=[
            ("termination", "إنهاء من صاحب العمل"),
            ("contract_end", "انتهاء عقد محدد المدة"),
            ("resignation", "استقالة (المادة 85)"),
            ("special_full", "حالة خاصة — استحقاق كامل (المادة 87)"),
            ("death", "وفاة أو عجز"),
            ("retirement", "تقاعد"),
            ("dismissal_80", "فصل لسبب نظامي (المادة 80)"),
        ],
        string="سبب انتهاء الخدمة",
        required=True,
        default="resignation",
        tracking=True,
        help="يحدّد السبب نسبة استحقاق المكافأة وفق نظام العمل.",
    )

    # ------- وعاء الأجر -------
    wage_base_policy = fields.Selection(
        selection=[
            ("full", "الأجر الشامل"),
            ("basic_housing", "الأساسي + السكن"),
            ("basic", "الأساسي فقط"),
        ],
        string="سياسة الوعاء",
        help="أساس استخراج الأجر من بيانات الموظف. تغييرها يُعيد حساب الوعاء.",
    )
    wage_base = fields.Monetary(
        string="الأجر الشهري (الوعاء)",
        currency_field="currency_id",
        tracking=True,
        help="الأجر الأخير الذي تُحسب عليه المكافأة (قابل للتعديل يدوياً).",
    )

    # ------- المخرجات المحسوبة -------
    service_days = fields.Integer(
        string="أيام الخدمة", compute="_compute_service", store=True
    )
    service_years = fields.Float(
        string="سنوات الخدمة", compute="_compute_service", store=True,
        digits=(16, 4),
    )
    gratuity_full = fields.Monetary(
        string="المكافأة الكاملة (قبل النسبة)",
        currency_field="currency_id",
        compute="_compute_gratuity", store=True,
    )
    entitlement_ratio = fields.Float(
        string="نسبة الاستحقاق",
        compute="_compute_gratuity", store=True, digits=(16, 4),
        help="النسبة المطبَّقة على المكافأة الكاملة وفق السبب ومدة الخدمة.",
    )
    gratuity_amount = fields.Monetary(
        string="مكافأة نهاية الخدمة المستحقة",
        currency_field="currency_id",
        compute="_compute_gratuity", store=True,
    )

    # ------- مستحقات/استقطاعات إضافية -------
    leave_balance_amount = fields.Monetary(
        string="بدل الإجازات", currency_field="currency_id",
        help="قيمة رصيد الإجازات المستحق نقداً.",
    )
    other_dues = fields.Monetary(
        string="مستحقات أخرى", currency_field="currency_id"
    )
    deductions = fields.Monetary(
        string="استقطاعات", currency_field="currency_id",
        help="سلف أو مديونيات تُخصم من المستحق.",
    )
    net_amount = fields.Monetary(
        string="صافي المستحق",
        currency_field="currency_id",
        compute="_compute_net", store=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("confirmed", "معتمدة"),
            ("posted", "مُرحَّلة محاسبياً"),
            ("paid", "مدفوعة"),
            ("cancel", "ملغاة"),
        ],
        string="الحالة", default="draft", tracking=True, copy=False,
    )
    move_id = fields.Many2one(
        "account.move", string="القيد المحاسبي", readonly=True, copy=False
    )
    notes = fields.Text(string="ملاحظات")

    # ============================================================
    # القيود
    # ============================================================
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    _("تاريخ انتهاء الخدمة لا يمكن أن يسبق تاريخ المباشرة.")
                )

    # ============================================================
    # الحسابات
    # ============================================================
    @api.depends("start_date", "end_date")
    def _compute_service(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                days = (rec.end_date - rec.start_date).days
                rec.service_days = days
                rec.service_years = days / 365.0
            else:
                rec.service_days = 0
                rec.service_years = 0.0

    @staticmethod
    def _base_gratuity(years, wage):
        """المكافأة الكاملة قبل تطبيق نسبة الاستقالة (المادة 84).

        نصف شهر لكل سنة من أول خمس سنوات، وشهر كامل لكل سنة بعدها،
        مع احتساب الكسور بالتناسب.
        """
        first_five = min(years, 5.0)
        beyond_five = max(years - 5.0, 0.0)
        months = (first_five * 0.5) + (beyond_five * 1.0)
        return wage * months

    @staticmethod
    def _resignation_ratio(years):
        """نسبة الاستحقاق عند الاستقالة وفق المادة 85."""
        if years < 2.0:
            return 0.0
        if years < 5.0:
            return 1.0 / 3.0
        if years < 10.0:
            return 2.0 / 3.0
        return 1.0

    @api.depends("service_years", "wage_base", "reason")
    def _compute_gratuity(self):
        for rec in self:
            full = rec._base_gratuity(rec.service_years, rec.wage_base or 0.0)
            rec.gratuity_full = full
            if rec.reason == "resignation":
                ratio = rec._resignation_ratio(rec.service_years)
            elif rec.reason == "dismissal_80":
                # الفصل النظامي (المادة 80) لا يستحق معه مكافأة افتراضياً
                ratio = 0.0
            else:
                # إنهاء صاحب العمل/انتهاء العقد/الوفاة/التقاعد/الحالات الخاصة
                ratio = 1.0
            rec.entitlement_ratio = ratio
            rec.gratuity_amount = full * ratio

    @api.depends(
        "gratuity_amount", "leave_balance_amount", "other_dues", "deductions"
    )
    def _compute_net(self):
        for rec in self:
            rec.net_amount = (
                (rec.gratuity_amount or 0.0)
                + (rec.leave_balance_amount or 0.0)
                + (rec.other_dues or 0.0)
                - (rec.deductions or 0.0)
            )

    # ============================================================
    # onchange مساعد: جلب وعاء الأجر من الموظف
    # ============================================================
    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for rec in self:
            emp = rec.employee_id
            if emp:
                if emp.company_id:
                    rec.company_id = emp.company_id
                rec.wage_base_policy = (
                    emp.company_id.rawasi_eos_wage_base_policy or "full"
                )
                rec.wage_base = emp._rawasi_eos_wage_base(rec.wage_base_policy)
                if emp.rawasi_join_date and not rec.start_date:
                    rec.start_date = emp.rawasi_join_date

    @api.onchange("wage_base_policy")
    def _onchange_wage_base_policy(self):
        for rec in self:
            if rec.employee_id and rec.wage_base_policy:
                rec.wage_base = rec.employee_id._rawasi_eos_wage_base(rec.wage_base_policy)

    # ============================================================
    # الإنشاء — التسلسل
    # ============================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("جديد")) == _("جديد"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.eos.settlement")
                    or _("جديد")
                )
        return super().create(vals_list)

    # ============================================================
    # دورة الحالة
    # ============================================================
    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("لا يمكن اعتماد إلا التسويات في حالة مسودة."))
            if not rec.wage_base:
                raise UserError(_("يجب تحديد وعاء الأجر قبل الاعتماد."))
            rec.state = "confirmed"

    def action_post_entry(self):
        """ترحيل القيد المحاسبي: مدين مخصص نهاية الخدمة / دائن مستحقات الموظف."""
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(_("يجب اعتماد التسوية قبل الترحيل المحاسبي."))
            if rec.move_id:
                raise UserError(_("سبق ترحيل قيد لهذه التسوية."))
            company = rec.company_id
            journal = company.rawasi_eos_journal_id
            debit_account = company.rawasi_eos_provision_account_id
            credit_account = company.rawasi_eos_payable_account_id
            if not (journal and debit_account and credit_account):
                raise UserError(
                    _(
                        "يرجى ضبط يومية نهاية الخدمة وحساباتها في إعدادات الشركة "
                        "(الإعدادات ← رواسي — الموارد البشرية)."
                    )
                )
            amount = rec.net_amount
            if amount <= 0:
                raise UserError(_("صافي المستحق صفر أو سالب؛ لا يوجد قيد للترحيل."))
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": rec.end_date,
                    "ref": _("نهاية خدمة: %s") % (rec.employee_id.name or rec.name),
                    "company_id": company.id,
                    "line_ids": [
                        (0, 0, {
                            "name": _("مكافأة نهاية الخدمة — %s") % rec.employee_id.name,
                            "account_id": debit_account.id,
                            "debit": amount,
                            "credit": 0.0,
                        }),
                        (0, 0, {
                            "name": _("مستحق نهاية الخدمة — %s") % rec.employee_id.name,
                            "account_id": credit_account.id,
                            "debit": 0.0,
                            "credit": amount,
                        }),
                    ],
                }
            )
            move.action_post()
            rec.move_id = move.id
            rec.state = "posted"

    def action_mark_paid(self):
        for rec in self:
            if rec.state not in ("confirmed", "posted"):
                raise UserError(_("لا يمكن تسجيل الدفع إلا بعد الاعتماد."))
            # انتهت الخدمة: نُصفِّر المخصص المتراكم للموظف (سُوِّي بالكامل)
            if rec.employee_id.rawasi_eos_accrued:
                rec.employee_id.rawasi_eos_accrued = 0.0
            rec.state = "paid"

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == "posted":
                raise UserError(
                    _("ألغِ القيد المحاسبي المرتبط أولاً قبل إلغاء التسوية.")
                )
            rec.state = "cancel"

    def action_reset_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_view_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }
