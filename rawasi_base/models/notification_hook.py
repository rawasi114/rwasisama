# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class RawasiNotificationHook(models.AbstractModel):
    """نقطة الإشعارات الموحَّدة لكل النظام.

    تُستدعى من المقاولات والورشة والتكامل عبر:
        self.env["rawasi.notification.hook"].send(record, event_type, recipients, extra)

    دائماً تكتب في chatter (مرجع تدقيق)، ثم ترسل عبر المزوّد المُعَد
    (داخلي / واتساب / SMS) حسب إعداد rawasi_base.notification_provider.
    """

    _name = "rawasi.notification.hook"
    _description = "نقطة إشعارات موحدة — رواسي"

    # ------------------------------------------------------------------
    # واجهة عامة
    # ------------------------------------------------------------------
    @api.model
    def send(self, record, event_type, recipients=None, extra=None):
        """يرسل إشعاراً موحداً عن حدث على سجل.

        :param record: سجل يدعم message_post (يرث mail.thread)
        :param event_type: مفتاح القالب (مثل "mr_issued")
        :param recipients: res.users (اختياري)
        :param extra: نص إضافي اختياري
        """
        if not record:
            return False
        icp = self.env["ir.config_parameter"].sudo()
        provider = icp.get_param("rawasi_base.notification_provider", "internal")
        body = self._format(record, event_type, extra)

        # 1) دائماً chatter
        partner_ids = []
        if recipients:
            partner_ids = recipients.mapped("partner_id").ids
        if hasattr(record, "message_post"):
            record.message_post(body=body, partner_ids=partner_ids)

        # 2) القناة الخارجية حسب الإعداد
        try:
            if provider == "whatsapp" and self._whatsapp_ready():
                self._send_whatsapp(record, body, recipients)
            elif provider == "sms":
                self._send_sms(record, body, recipients)
        except Exception as exc:  # لا تُفشل عملية الأعمال بسبب الإشعار
            _logger.warning("rawasi notification external channel failed: %s", exc)
        return True

    # ------------------------------------------------------------------
    # القنوات
    # ------------------------------------------------------------------
    def _whatsapp_ready(self):
        icp = self.env["ir.config_parameter"].sudo()
        return bool(
            icp.get_param("rawasi_base.whatsapp_endpoint")
            and icp.get_param("rawasi_base.whatsapp_token")
        )

    def _send_whatsapp(self, record, body, recipients):
        """Stub قابل للاستبدال بمزوّد فعلي (Twilio/WAHA/Meta Cloud)."""
        _logger.info("WhatsApp send (stub): %s -> %s", body[:60], recipients and recipients.ids)

    def _send_sms(self, record, body, recipients):
        if "sms.sms" not in self.env:
            _logger.info("SMS module not installed; skipping SMS for: %s", body[:60])
            return
        for user in recipients or self.env["res.users"]:
            number = user.partner_id.mobile or user.partner_id.phone
            if number:
                self.env["sms.sms"].sudo().create({"body": body, "number": number}).send()

    # ------------------------------------------------------------------
    # القوالب
    # ------------------------------------------------------------------
    def _format(self, record, event_type, extra):
        templates = self._get_templates()
        tmpl = templates.get(event_type, "%(name)s — %(event)s")
        try:
            msg = tmpl % {"name": record.display_name, "event": event_type}
        except (KeyError, TypeError):
            msg = "%s — %s" % (record.display_name, event_type)
        if extra:
            msg = "%s\n%s" % (msg, extra)
        return msg

    def _get_templates(self):
        """قوالب أساسية؛ يُوسِّعها كل موديول فرعي بـ super()."""
        return {
            "approval_overdue": "اعتماد متأخر: %(name)s",
            "admin_override": "تجاوز إداري: %(name)s",
        }
