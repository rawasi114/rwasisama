# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiAuditTrail(models.Model):
    """سجل تدقيق موحَّد (append-only) يتلقّى تسجيلات من كل الموديولات.

    يُكتب عبر الدالة المساعدة:
        self.env["rawasi.audit.trail"].log(record, "override", reason="...", detail="...")
    التي تُنشئ السجل بصلاحية النظام (sudo) لضمان التسجيل بصرف النظر عن صلاحية المستخدم.
    """

    _name = "rawasi.audit.trail"
    _description = "سجل تدقيق — رواسي"
    _order = "create_date desc, id desc"

    name = fields.Char(string="الوصف", required=True)
    event = fields.Selection(
        selection=[
            ("create", "إنشاء"),
            ("write", "تعديل"),
            ("approve", "اعتماد"),
            ("override", "تجاوز إداري"),
            ("cancel", "إلغاء"),
            ("delete", "حذف"),
            ("issue", "صرف"),
            ("other", "أخرى"),
        ],
        string="الحدث",
        required=True,
        default="other",
        index=True,
    )
    model_name = fields.Char(string="النموذج", index=True)
    res_id = fields.Integer(string="معرّف السجل", index=True)
    res_name = fields.Char(string="اسم السجل")
    user_id = fields.Many2one(
        "res.users", string="المستخدم", required=True, default=lambda self: self.env.user.id, index=True
    )
    event_date = fields.Datetime(
        string="التاريخ", required=True, default=fields.Datetime.now, index=True
    )
    reason = fields.Text(string="السبب")
    detail = fields.Text(string="التفاصيل")
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    # ------------------------------------------------------------------
    # واجهة التسجيل
    # ------------------------------------------------------------------
    @api.model
    def log(self, record=None, event="other", reason=None, detail=None, name=None):
        """يسجّل حدثاً في سجل التدقيق (بصلاحية النظام)."""
        vals = {
            "event": event,
            "reason": reason,
            "detail": detail,
            "user_id": self.env.uid,
        }
        if record is not None and record:
            vals.update(
                {
                    "model_name": record._name,
                    "res_id": record.id,
                    "res_name": record.display_name,
                }
            )
        vals["name"] = name or self._default_name(record, event)
        return self.sudo().create(vals)

    def _default_name(self, record, event):
        label = dict(self._fields["event"].selection).get(event, event)
        if record is not None and record:
            return "%s: %s" % (label, record.display_name)
        return label

    # ------------------------------------------------------------------
    # append-only: منع التعديل والحذف نهائياً (حتى بصلاحية النظام)
    # السجل يُنشأ فقط عبر log()، ولا يُعدَّل أو يُحذف أبداً — لضمان نزاهة التدقيق.
    # ------------------------------------------------------------------
    def write(self, vals):
        raise UserError("سجل التدقيق للقراءة فقط — لا يمكن تعديله.")

    def unlink(self):
        raise UserError("سجل التدقيق للقراءة فقط — لا يمكن حذفه.")
