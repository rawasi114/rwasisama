# -*- coding: utf-8 -*-
from odoo import models


class RawasiNotificationHook(models.AbstractModel):
    """يوسّع قوالب الإشعارات بأحداث الورشة."""

    _inherit = "rawasi.notification.hook"

    def _get_templates(self):
        templates = super()._get_templates()
        templates.update(
            {
                "mo_confirmed": "تأكيد أمر تصنيع: %(name)s",
                "mo_in_production": "بدء تصنيع: %(name)s",
                "mo_done": "اكتمل تصنيع: %(name)s",
                "mo_delivered": "تسليم أمر تصنيع: %(name)s",
                "mr_approved": "طلب مواد ورشة اعتمده المشرف: %(name)s",
                "mr_budget_ok": "طلب مواد ورشة اعتمدته الحسابات: %(name)s",
                "mr_in_purchase": "طلب مواد ورشة محوَّل للمشتريات: %(name)s",
                "mr_issued": "تم صرف مواد الورشة: %(name)s",
                "mr_cancelled": "أُلغي طلب مواد الورشة: %(name)s",
            }
        )
        return templates
