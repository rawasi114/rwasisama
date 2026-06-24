# -*- coding: utf-8 -*-
import base64
import csv
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiWpsBatch(models.Model):
    """دفعة حماية الأجور (WPS) — توليد ملف SIF بصيغة مدد.

    تُجمَّع رواتب الموظفين عن شهرٍ محدد في دفعة واحدة، ثم يُولَّد ملف نصي
    (CSV/SIF) يحتوي سجلّ المنشأة وسجلات الموظفين (الآيبان والأجر الأساسي
    والبدلات والاستقطاعات والصافي)، قابل للتنزيل ورفعه لبوابة البنك/مدد.

    ملاحظة: الصيغة هنا متوافقة مع الأعمدة القياسية لملف حماية الأجور؛ قد
    يتطلب بنك بعينه تعديلاً طفيفاً في الترتيب أو الفواصل، ويُضبط بسهولة هنا.
    """

    _name = "rawasi.wps.batch"
    _description = "دفعة حماية الأجور"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, month desc, id desc"

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
    month = fields.Selection(
        selection=[(str(m), str(m)) for m in range(1, 13)],
        string="الشهر", required=True,
    )
    year = fields.Integer(string="السنة", required=True)

    line_ids = fields.One2many(
        "rawasi.wps.line", "batch_id", string="سطور الرواتب"
    )
    employee_count = fields.Integer(
        string="عدد الموظفين", compute="_compute_totals", store=True
    )
    total_net = fields.Monetary(
        string="إجمالي الصافي", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("generated", "تم توليد الملف"),
            ("sent", "مُرسلة للبنك"),
            ("cancel", "ملغاة"),
        ],
        string="الحالة", default="draft", tracking=True, copy=False,
    )
    sif_file = fields.Binary(string="ملف حماية الأجور (SIF)", readonly=True, copy=False)
    sif_filename = fields.Char(string="اسم الملف", readonly=True, copy=False)

    @api.depends("line_ids.net_salary")
    def _compute_totals(self):
        for batch in self:
            batch.employee_count = len(batch.line_ids)
            batch.total_net = sum(batch.line_ids.mapped("net_salary"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("جديد")) == _("جديد"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.wps.batch")
                    or _("جديد")
                )
        return super().create(vals_list)

    # ============================================================
    # تعبئة السطور من الموظفين
    # ============================================================
    def action_populate_lines(self):
        """تعبئة سطور الدفعة من موظفي الشركة الذين لديهم تركيبة أجر."""
        for batch in self:
            batch.line_ids.unlink()
            employees = self.env["hr.employee"].search([
                ("company_id", "=", batch.company_id.id),
                ("rawasi_total_wage", ">", 0),
            ])
            if not employees:
                raise UserError(
                    _("لا يوجد موظفون بتركيبة أجر معرَّفة في هذه الشركة.")
                )
            lines = []
            for emp in employees:
                lines.append((0, 0, {
                    "employee_id": emp.id,
                    "basic_salary": emp.rawasi_basic_wage,
                    "housing_allowance": emp.rawasi_housing_allowance,
                    "other_allowance": emp.rawasi_other_allowance,
                    "deductions": 0.0,
                }))
            batch.line_ids = lines

    # ============================================================
    # توليد ملف SIF
    # ============================================================
    def action_generate_file(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("أضف سطور رواتب قبل توليد الملف."))
        company = self.company_id
        if not company.rawasi_mol_establishment_id:
            raise UserError(
                _("يرجى تعيين «رقم المنشأة في مكتب العمل» في إعدادات الشركة.")
            )
        bank = company.rawasi_wps_bank_id

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        # سجل المنشأة (Header / Employer Record)
        writer.writerow([
            "EMPLOYER",
            company.rawasi_mol_establishment_id,
            company.name or "",
            bank.acc_number if bank else "",
            "%s-%s" % (self.year, str(self.month).zfill(2)),
            len(self.line_ids),
            "%.2f" % self.total_net,
            self.currency_id.name or "SAR",
        ])
        # سجلات الموظفين (Salary Detail Records)
        for line in self.line_ids:
            emp = line.employee_id
            if not emp.rawasi_bank_iban:
                raise UserError(
                    _("الموظف %s ليس له آيبان (IBAN) مُعرَّف.") % emp.name
                )
            writer.writerow([
                "SALARY",
                emp.rawasi_mol_number or "",
                emp.name or "",
                emp.rawasi_bank_iban,
                emp.rawasi_bank_code or "",
                "%.2f" % line.basic_salary,
                "%.2f" % line.housing_allowance,
                "%.2f" % line.other_allowance,
                "%.2f" % line.deductions,
                "%.2f" % line.net_salary,
            ])

        content = buffer.getvalue().encode("utf-8-sig")
        self.sif_file = base64.b64encode(content)
        self.sif_filename = "WPS_%s_%s%s.csv" % (
            company.rawasi_mol_establishment_id, self.year, str(self.month).zfill(2)
        )
        self.state = "generated"

    def action_mark_sent(self):
        for batch in self:
            if batch.state != "generated":
                raise UserError(_("ولّد الملف أولاً قبل التأشير بالإرسال."))
            batch.state = "sent"

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset_draft(self):
        self.write({"state": "draft"})


class RawasiWpsLine(models.Model):
    """سطر راتب موظف ضمن دفعة حماية الأجور."""

    _name = "rawasi.wps.line"
    _description = "سطر حماية الأجور"

    batch_id = fields.Many2one(
        "rawasi.wps.batch", string="الدفعة", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    currency_id = fields.Many2one(related="batch_id.currency_id", store=True)
    employee_id = fields.Many2one(
        "hr.employee", string="الموظف", required=True, ondelete="restrict"
    )
    iban = fields.Char(string="الآيبان", related="employee_id.rawasi_bank_iban")

    basic_salary = fields.Monetary(string="الأساسي", currency_field="currency_id")
    housing_allowance = fields.Monetary(string="بدل السكن", currency_field="currency_id")
    other_allowance = fields.Monetary(string="بدلات أخرى", currency_field="currency_id")
    deductions = fields.Monetary(string="استقطاعات", currency_field="currency_id")
    net_salary = fields.Monetary(
        string="الصافي", currency_field="currency_id",
        compute="_compute_net_salary", store=True,
    )

    @api.depends("basic_salary", "housing_allowance", "other_allowance", "deductions")
    def _compute_net_salary(self):
        for line in self:
            line.net_salary = (
                (line.basic_salary or 0.0)
                + (line.housing_allowance or 0.0)
                + (line.other_allowance or 0.0)
                - (line.deductions or 0.0)
            )
