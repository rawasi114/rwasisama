# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiEosProvisionRun(models.Model):
    """دفعة مخصص شهري لمكافأة نهاية الخدمة.

    المعالجة المحاسبية القياسية: يُحمَّل التزام نهاية الخدمة تدريجياً على مدى
    سنوات الخدمة. في كل تشغيل نحسب لكل موظف الالتزام المستهدف حتى تاريخ الدفعة
    (المكافأة الكاملة وفق المادة 84 لو انتهت خدمته اليوم)، ثم نُرحِّل الفرق بين
    المستهدف وما سبق تراكمه كمصروف الشهر:

        مدين: مصروف مكافأة نهاية الخدمة
        دائن: مخصص مكافأة نهاية الخدمة (التزام)
    """

    _name = "rawasi.eos.provision.run"
    _description = "دفعة مخصص نهاية الخدمة"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "provision_date desc, id desc"

    name = fields.Char(
        string="المرجع", required=True, copy=False, readonly=True, index=True,
        default=lambda self: _("جديد"),
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="العملة",
        default=lambda self: self.env.company.currency_id.id,
    )
    provision_date = fields.Date(
        string="تاريخ المخصص", required=True,
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        "rawasi.eos.provision.line", "run_id", string="السطور"
    )
    total_provision = fields.Monetary(
        string="إجمالي المخصص", currency_field="currency_id",
        compute="_compute_total", store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("posted", "مُرحَّلة"),
            ("cancel", "ملغاة"),
        ],
        string="الحالة", default="draft", tracking=True, copy=False,
    )
    move_id = fields.Many2one(
        "account.move", string="القيد المحاسبي", readonly=True, copy=False
    )

    @api.depends("line_ids.provision_amount")
    def _compute_total(self):
        for run in self:
            run.total_provision = sum(run.line_ids.mapped("provision_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("جديد")) == _("جديد"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.eos.provision.run")
                    or _("جديد")
                )
        return super().create(vals_list)

    def action_compute_lines(self):
        """حساب المخصص المستحق لكل موظف لديه تاريخ التحاق ووعاء أجر."""
        Settlement = self.env["rawasi.eos.settlement"]
        for run in self:
            run.line_ids.unlink()
            employees = self.env["hr.employee"].search([
                ("company_id", "=", run.company_id.id),
                ("rawasi_join_date", "!=", False),
                ("rawasi_total_wage", ">", 0),
            ])
            lines = []
            for emp in employees:
                if emp.rawasi_join_date > run.provision_date:
                    continue
                days = (run.provision_date - emp.rawasi_join_date).days
                years = days / 365.0
                wage = emp._rawasi_eos_wage_base()
                target = Settlement._base_gratuity(years, wage)
                # لا نعكس الالتزام عند انخفاض المستهدف؛ نأخذ الفرق الموجب فقط
                provision = max(target - (emp.rawasi_eos_accrued or 0.0), 0.0)
                lines.append((0, 0, {
                    "employee_id": emp.id,
                    "service_years": years,
                    "wage_base": wage,
                    "target_liability": target,
                    "previously_accrued": emp.rawasi_eos_accrued or 0.0,
                    "provision_amount": provision,
                }))
            if not lines:
                raise UserError(
                    _("لا يوجد موظفون مؤهلون (يلزم تاريخ التحاق ووعاء أجر).")
                )
            run.line_ids = lines

    def action_post(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("لا يمكن ترحيل إلا الدفعات في حالة مسودة."))
        if not self.line_ids:
            raise UserError(_("احسب السطور أولاً."))
        company = self.company_id
        journal = company.rawasi_eos_journal_id
        expense = company.rawasi_eos_expense_account_id
        liability = company.rawasi_eos_provision_account_id
        if not (journal and expense and liability):
            raise UserError(
                _(
                    "يرجى ضبط يومية نهاية الخدمة وحساب المصروف وحساب المخصص "
                    "في إعدادات الشركة."
                )
            )
        amount = self.total_provision
        if amount <= 0:
            raise UserError(_("إجمالي المخصص صفر؛ لا يوجد قيد للترحيل."))
        move = self.env["account.move"].create({
            "move_type": "entry",
            "journal_id": journal.id,
            "date": self.provision_date,
            "ref": _("مخصص نهاية الخدمة — %s") % self.name,
            "company_id": company.id,
            "line_ids": [
                (0, 0, {
                    "name": _("مصروف مخصص نهاية الخدمة"),
                    "account_id": expense.id,
                    "debit": amount,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": _("مخصص نهاية الخدمة (التزام)"),
                    "account_id": liability.id,
                    "debit": 0.0,
                    "credit": amount,
                }),
            ],
        })
        move.action_post()
        # تحديث المتراكم لكل موظف
        for line in self.line_ids:
            line.employee_id.rawasi_eos_accrued = (
                (line.employee_id.rawasi_eos_accrued or 0.0) + line.provision_amount
            )
        self.move_id = move.id
        self.state = "posted"

    def action_cancel(self):
        for run in self:
            if run.move_id and run.move_id.state == "posted":
                raise UserError(_("ألغِ القيد المرتبط أولاً."))
            run.state = "cancel"

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

    @api.model
    def _cron_monthly_provision(self):
        """مهمة شهرية: تنشئ دفعة مخصص وتحسبها وتُرحِّلها لكل شركة مهيّأة."""
        companies = self.env["res.company"].search([
            ("rawasi_eos_journal_id", "!=", False),
            ("rawasi_eos_expense_account_id", "!=", False),
            ("rawasi_eos_provision_account_id", "!=", False),
        ])
        for company in companies:
            run = self.with_company(company).create({"company_id": company.id})
            try:
                run.action_compute_lines()
                run.action_post()
            except UserError:
                # لا موظفين مؤهلين أو لا مخصص لهذه الشركة — نتخطّى بهدوء
                run.unlink()


class RawasiEosProvisionLine(models.Model):
    """سطر مخصص نهاية الخدمة لموظف ضمن دفعة."""

    _name = "rawasi.eos.provision.line"
    _description = "سطر مخصص نهاية الخدمة"

    run_id = fields.Many2one(
        "rawasi.eos.provision.run", string="الدفعة", required=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="run_id.currency_id", store=True)
    employee_id = fields.Many2one(
        "hr.employee", string="الموظف", required=True, ondelete="restrict"
    )
    service_years = fields.Float(string="سنوات الخدمة", digits=(16, 2))
    wage_base = fields.Monetary(string="وعاء الأجر", currency_field="currency_id")
    target_liability = fields.Monetary(
        string="الالتزام المستهدف", currency_field="currency_id"
    )
    previously_accrued = fields.Monetary(
        string="المتراكم سابقاً", currency_field="currency_id"
    )
    provision_amount = fields.Monetary(
        string="مخصص الشهر", currency_field="currency_id"
    )
