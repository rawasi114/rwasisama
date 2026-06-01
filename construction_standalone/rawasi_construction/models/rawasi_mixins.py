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

    def _ensure_finance_user(self):
        """حارس عمليات الدفع: يسمح للمحاسب أو المدير العام أو الأدمن فقط."""
        u = self.env.user
        if (self.env.su
                or u.has_group("base.group_system")
                or u.has_group("rawasi_construction.group_ceo")
                or u.has_group("rawasi_construction.group_accountant")):
            return
        raise UserError(_(
            "تسجيل الدفع متاح للمحاسب أو المدير العام فقط. "
            "تواصل مع المحاسب لإتمام الدفع."
        ))

    def _ensure_tech_approver(self):
        """حارس الاعتماد الفني: مدير المكتب الفني أو مدير المشاريع أو الأعلى."""
        u = self.env.user
        if (self.env.su
                or u.has_group("base.group_system")
                or u.has_group("rawasi_construction.group_ceo")
                or u.has_group("rawasi_construction.group_projects_director")
                or u.has_group("rawasi_construction.group_tech_office_manager")):
            return
        raise UserError(_(
            "اعتماد/رفض المستند متاح لمدير المكتب الفني أو مدير المشاريع فقط."
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
        report_xmlid = self._report_xmlid()
        pdf, _dummy = self.env["ir.actions.report"]._render_qweb_pdf(
            report_xmlid, res_ids=self.ids
        )
        streams = [pdf]
        for att in self.attachment_ids.sorted("id"):
            if att.mimetype == "application/pdf" and att.datas:
                streams.append(base64.b64decode(att.datas))
        merged = merge_pdf(streams)
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
