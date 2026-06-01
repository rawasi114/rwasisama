# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RawasiApprovalChain(models.Model):
    """محرك سلاسل اعتماد قابل للإعداد + تصعيد آلي.

    سلسلة لكل نموذج أعمال (مثل rawasi.material.request)، تتكوّن من خطوات
    مرتبة كل منها لمجموعة صلاحيات. التصعيد الآلي عبر cron يومي.
    """

    _name = "rawasi.approval.chain"
    _description = "سلسلة اعتماد — رواسي"
    _order = "name"

    name = fields.Char(string="الاسم", required=True)
    model = fields.Char(string="النموذج المستهدف", required=True, help="مثال: rawasi.material.request")
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("rawasi.approval.step", "chain_id", string="الخطوات")
    escalation_hours = fields.Integer(string="ساعات التصعيد", default=48)
    escalation_user_id = fields.Many2one("res.users", string="مستخدم التصعيد")
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    # ------------------------------------------------------------------
    # التصعيد الآلي
    # ------------------------------------------------------------------
    @api.model
    def _cron_escalate_overdue(self):
        """يفحص النشاطات المتأخرة ويذكّر بها عبر نقطة الإشعارات الموحدة.

        آمن للتشغيل حتى مع عدم وجود سلاسل/طلبات: يكتفي بالنشاطات المتأخرة
        المرتبطة بنماذج رواسي.
        """
        icp = self.env["ir.config_parameter"].sudo()
        try:
            hours = int(icp.get_param("rawasi_base.escalation_hours", 48))
        except (TypeError, ValueError):
            hours = 48
        cutoff = fields.Date.context_today(self) - timedelta(days=max(1, hours // 24))
        activities = self.env["mail.activity"].sudo().search(
            [("date_deadline", "<", cutoff)]
        )
        rawasi_acts = activities.filtered(
            lambda a: a.res_model and a.res_model.startswith("rawasi.")
        )
        hook = self.env["rawasi.notification.hook"]
        for act in rawasi_acts:
            record = self.env[act.res_model].browse(act.res_id).exists()
            if not record:
                continue
            recipients = act.user_id
            hook.send(
                record,
                "approval_overdue",
                recipients=recipients,
                extra="نشاط متأخر منذ %s" % act.date_deadline,
            )
        if rawasi_acts:
            _logger.info("rawasi escalation: notified %s overdue activities", len(rawasi_acts))
        return True


class RawasiApprovalStep(models.Model):
    _name = "rawasi.approval.step"
    _description = "خطوة اعتماد — رواسي"
    _order = "chain_id, sequence, id"

    chain_id = fields.Many2one(
        "rawasi.approval.chain", string="السلسلة", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(string="التسلسل", default=10)
    name = fields.Char(string="اسم الخطوة", required=True)
    group_id = fields.Many2one("res.groups", string="مجموعة الاعتماد", required=True)
    is_optional = fields.Boolean(string="اختيارية", default=False)
    allow_admin_shortcut = fields.Boolean(string="يسمح باختصار الأدمن", default=True)
