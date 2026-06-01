# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiNcr(models.Model):
    _name = "rawasi.ncr"
    _description = "تقرير عدم مطابقة (Non-Conformance Report)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "create_date desc"

    name = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    # رابط اختياري لبند جدول الكميات
    boq_item_id = fields.Many2one("rawasi.boq.item", string="بند جدول الكميات")
    subject = fields.Char(string="الموضوع", required=True, tracking=True)
    description = fields.Text(string="وصف عدم المطابقة", required=True)
    severity = fields.Selection(
        [("minor", "بسيط"), ("major", "جسيم"), ("critical", "حرج")],
        string="الخطورة",
        default="minor",
        required=True,
        tracking=True,
    )
    raised_by_id = fields.Many2one(
        "res.users", string="رفعه", default=lambda self: self.env.user
    )
    issue_date = fields.Date(
        string="تاريخ الرصد", default=fields.Date.context_today
    )
    root_cause = fields.Text(string="السبب الجذري")
    corrective_action = fields.Text(string="الإجراء التصحيحي")
    responsible_id = fields.Many2one("res.users", string="المسؤول عن المعالجة")
    due_date = fields.Date(string="تاريخ الاستحقاق")
    closed_date = fields.Date(string="تاريخ الإغلاق", readonly=True, copy=False)
    state = fields.Selection(
        [
            ("open", "مفتوح"),
            ("in_progress", "قيد المعالجة"),
            ("closed", "مغلق"),
            ("void", "ملغى"),
        ],
        string="الحالة",
        default="open",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_ncr_attachment_rel",
        "ncr_id",
        "attachment_id",
        string="المرفقات",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    # ═══ التصعيد لـ RFI ═══
    rfi_ids = fields.One2many(
        "rawasi.rfi", "ncr_id", string="طلبات المعلومات المرتبطة",
    )
    rfi_count = fields.Integer(
        string="عدد RFI", compute="_compute_rfi_count",
    )
    is_overdue = fields.Boolean(
        string="متأخّر", compute="_compute_is_overdue", store=True,
    )
    can_escalate = fields.Boolean(
        string="يمكن التصعيد", compute="_compute_can_escalate",
    )

    @api.depends("rfi_ids")
    def _compute_rfi_count(self):
        for r in self:
            r.rfi_count = len(r.rfi_ids)

    @api.depends("due_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for r in self:
            r.is_overdue = (
                r.due_date
                and r.due_date < today
                and r.state in ("open", "in_progress")
            )

    @api.depends("severity", "state", "is_overdue", "rfi_count")
    def _compute_can_escalate(self):
        for r in self:
            r.can_escalate = (
                r.severity in ("major", "critical")
                and r.state in ("open", "in_progress")
                and r.rfi_count == 0
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.ncr"
                ) or "/"
        return super().create(vals_list)

    def _report_xmlid(self):
        return "rawasi_construction.action_report_ncr"

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_close(self):
        self.write({"state": "closed", "closed_date": fields.Date.context_today(self)})

    def action_void(self):
        self._ensure_admin()
        self.write({"state": "void"})

    def action_reopen(self):
        self._ensure_admin()
        self.write({"state": "open", "closed_date": False})

    # ═══ تصعيد NCR إلى RFI ═══
    def action_escalate_to_rfi(self):
        """ينشئ RFI مرتبطاً بهذا NCR ويفتح فورم الـ RFI الجديد."""
        self.ensure_one()
        if not self.can_escalate:
            raise UserError(_(
                "لا يمكن التصعيد: NCR إمّا منخفض الخطورة أو مغلق أو سبق تصعيده."
            ))
        rfi = self.env["rawasi.rfi"].create({
            "project_id": self.project_id.id,
            "boq_item_id": self.boq_item_id.id or False,
            "subject": _("تصعيد NCR %s — %s") % (self.name, self.subject),
            "question": _(
                "تصعيد تلقائي من NCR رقم %(num)s.\n\n"
                "وصف عدم المطابقة:\n%(desc)s\n\n"
                "السبب الجذري:\n%(root)s\n\n"
                "نطلب توجيهاً رسمياً للمعالجة."
            ) % {
                "num": self.name,
                "desc": self.description or "",
                "root": self.root_cause or "(لم يُحدَّد بعد)",
            },
            "ncr_id": self.id,
            "priority": "high" if self.severity == "critical" else "medium",
        })
        self.message_post(body=_(
            "تم تصعيد NCR إلى RFI: <a href='#' data-oe-model='rawasi.rfi' "
            "data-oe-id='%d'>%s</a>"
        ) % (rfi.id, rfi.name or _("RFI جديد")))
        return {
            "type": "ir.actions.act_window",
            "name": _("طلب المعلومات الجديد"),
            "res_model": "rawasi.rfi",
            "res_id": rfi.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_rfis(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("RFI المرتبطة بـ %s") % self.name,
            "res_model": "rawasi.rfi",
            "view_mode": "list,form",
            "domain": [("ncr_id", "=", self.id)],
            "context": {"default_ncr_id": self.id,
                        "default_project_id": self.project_id.id},
        }
