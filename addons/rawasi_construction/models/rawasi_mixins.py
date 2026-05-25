# -*- coding: utf-8 -*-
import base64

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.pdf import merge_pdf


class RawasiWorkflowMixin(models.AbstractModel):
    """حارس العمليات الحسّاسة: الإلغاء والحذف والإرجاع لمسودة لمستخدمي الإدارة فقط.

    القاعدة المؤسسية: أي شيء يُسجَّل في النظام لا يُلغى ولا يُعاد لمسودة ولا يُحذف
    إلا من قِبل مستخدم إدارة (Admin = base.group_system)، حيثما أمكن.
    """
    _name = "rawasi.workflow.mixin"
    _description = "حارس صلاحيات الإلغاء/الحذف (Admin فقط)"

    def _ensure_admin(self):
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        raise UserError(_(
            "هذه العملية (إلغاء / إعادة لمسودة / حذف) متاحة لمستخدمي الإدارة (Admin) فقط. "
            "البنود المُسجَّلة تبقى للسجل المؤسسي."
        ))


class RawasiPrintableMixin(models.AbstractModel):
    """طباعة تقرير PDF لكل حقول النموذج، مع خيار دمج مرفقات الـ PDF في ملف واحد."""
    _name = "rawasi.printable.mixin"
    _description = "طباعة تقرير مع دمج المرفقات"

    def _report_xmlid(self):
        """يُعيد المعرّف الكامل لإجراء تقرير QWeb الخاص بالنموذج (يُعاد تعريفه)."""
        raise NotImplementedError()

    def action_print_with_attachments(self):
        """يولّد تقرير النموذج ويدمجه مع مرفقات الـ PDF في ملف واحد قابل للتنزيل."""
        self.ensure_one()
        report_obj = self.env["ir.actions.report"]
        report_xmlid = self._report_xmlid()
        # نولّد التقرير بلا ختم ثم نختم الملف المدموج كاملاً (التقرير + المرفقات)
        pdf, _dummy = report_obj.with_context(rawasi_skip_stamp=True)._render_qweb_pdf(
            report_xmlid, res_ids=self.ids
        )
        streams = [pdf]
        for att in self.attachment_ids.sorted("id"):
            if att.mimetype == "application/pdf" and att.datas:
                streams.append(base64.b64decode(att.datas))
        merged = merge_pdf(streams)
        stamp_bytes = report_obj._rawasi_company_stamp()
        if stamp_bytes:
            try:
                merged = report_obj._rawasi_overlay_stamp(merged, stamp_bytes)
            except Exception:
                pass
        fname = (self.display_name or "document").replace("/", "-")
        attachment = self.env["ir.attachment"].create({
            "name": "%s.pdf" % fname,
            "type": "binary",
            "datas": base64.b64encode(merged),
            "mimetype": "application/pdf",
            "res_model": self._name,
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
