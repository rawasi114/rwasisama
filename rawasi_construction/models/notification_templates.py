# -*- coding: utf-8 -*-
from odoo import models


class RawasiNotificationHook(models.AbstractModel):
    """يوسّع قوالب الإشعارات بأحداث المقاولات."""

    _inherit = "rawasi.notification.hook"

    def _get_templates(self):
        templates = super()._get_templates()
        templates.update(
            {
                "mr_approved": "طلب مواد اعتمده المشرف: %(name)s",
                "mr_budget_ok": "طلب مواد اعتمدته الحسابات: %(name)s",
                "mr_in_purchase": "طلب مواد محوَّل للمشتريات: %(name)s",
                "mr_issued": "تم صرف طلب المواد: %(name)s",
                "mr_cancelled": "أُلغي طلب المواد: %(name)s",
                "guarantee_expiring": "خطاب ضمان قارب الانتهاء: %(name)s",
                "ipc_submitted": "مستخلص مقدَّم: %(name)s",
            }
        )
        return templates
