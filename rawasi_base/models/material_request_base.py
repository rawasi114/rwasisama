# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiMaterialRequestBase(models.AbstractModel):
    """قاعدة طلب المواد المجرّدة — المشتركة بين المقاولات والورشة.

    تحمل سير الاعتماد الموحّد وحقول التدقيق والأزرار، ويرث منها كل موديول
    فرعي نموذجاً ملموساً يضيف حقوله (project_id / section_id ...) ويُنفّذ
    _do_issue() لتحديد مصدر/وجهة الصرف.

    AbstractModel: لا يُنشأ له جدول.
    """

    _name = "rawasi.material.request.base"
    _description = "قاعدة طلب المواد (مجردة) — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    # رمز التسلسل الذي يستخدمه النموذج الملموس لتوليد الاسم (يتجاوزه الوارث)
    _mr_sequence_code = None

    name = fields.Char(string="المرجع", default="جديد", readonly=True, copy=False, index=True)
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("approved_supervisor", "اعتمد المشرف"),
            ("approved_budget", "اعتمد الحسابات"),
            ("in_purchase", "محوَّل للمشتريات"),
            ("issued", "صادر"),
            ("cancelled", "ملغى"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
        index=True,
    )
    urgency = fields.Selection(
        selection=[("low", "عادي"), ("medium", "متوسط"), ("high", "عاجل")],
        string="الأهمية",
        default="medium",
        tracking=True,
    )
    requester_id = fields.Many2one(
        "res.users", string="مقدّم الطلب", default=lambda self: self.env.user.id, readonly=True
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )
    note = fields.Text(string="ملاحظات")

    # حقول تدقيق سير الاعتماد
    supervisor_user_id = fields.Many2one("res.users", string="معتمِد المشرف", readonly=True)
    supervisor_date = fields.Datetime(string="تاريخ اعتماد المشرف", readonly=True)
    accountant_user_id = fields.Many2one("res.users", string="معتمِد الحسابات", readonly=True)
    accountant_date = fields.Datetime(string="تاريخ اعتماد الحسابات", readonly=True)
    purchase_user_id = fields.Many2one("res.users", string="محوِّل المشتريات", readonly=True)
    purchase_date = fields.Datetime(string="تاريخ التحويل للمشتريات", readonly=True)
    issuer_user_id = fields.Many2one("res.users", string="القائم بالصرف", readonly=True)
    issue_date = fields.Datetime(string="تاريخ الصرف", readonly=True)

    # ------------------------------------------------------------------
    # إنشاء — توليد الاسم من التسلسل الذي يحدده الوارث
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                seq_code = self._mr_sequence_code
                if seq_code:
                    vals["name"] = self.env["ir.sequence"].next_by_code(seq_code) or "جديد"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # أزرار سير الاعتماد
    # ------------------------------------------------------------------
    def action_approve_supervisor(self):
        self._require_state(["draft"])
        self.write(
            {
                "state": "approved_supervisor",
                "supervisor_user_id": self.env.uid,
                "supervisor_date": fields.Datetime.now(),
            }
        )
        self._notify("mr_approved")
        return True

    def action_approve_budget(self):
        self._require_state(["approved_supervisor"])
        self._check_budget()
        self.write(
            {
                "state": "approved_budget",
                "accountant_user_id": self.env.uid,
                "accountant_date": fields.Datetime.now(),
            }
        )
        self._notify("mr_budget_ok")
        return True

    def action_forward_purchase(self):
        self._require_state(["approved_budget"])
        self.write(
            {
                "state": "in_purchase",
                "purchase_user_id": self.env.uid,
                "purchase_date": fields.Datetime.now(),
            }
        )
        self._notify("mr_in_purchase")
        return True

    def action_issue(self):
        """يصرف المواد. يفرض PIN إن كان مفعّلاً، ثم يستدعي _do_issue للوارث."""
        self._require_state(["in_purchase"])
        if self._require_pin() and not self.env.context.get("pin_verified"):
            return self._open_pin_wizard("action_issue")
        self._do_issue()
        self.write(
            {
                "state": "issued",
                "issuer_user_id": self.env.uid,
                "issue_date": fields.Datetime.now(),
            }
        )
        self._notify("mr_issued")
        return True

    def action_cancel(self):
        self._require_state(["draft", "approved_supervisor", "approved_budget", "in_purchase"])
        self.write({"state": "cancelled"})
        self._notify("mr_cancelled")
        return True

    def action_reset_draft(self):
        self._require_state(["cancelled"])
        self.write({"state": "draft"})
        return True

    # ------------------------------------------------------------------
    # نقاط امتداد للوارث
    # ------------------------------------------------------------------
    def _do_issue(self):
        """يُنفّذ حركة الصرف الفعلية. يجب تجاوزها في الموديول الفرعي."""
        raise NotImplementedError("يجب تجاوز _do_issue في النموذج الفرعي.")

    def _check_budget(self):
        """فحص الميزانية قبل اعتماد الحسابات. يتجاوزه الوارث عند الحاجة."""
        return True

    # ------------------------------------------------------------------
    # مساعدات
    # ------------------------------------------------------------------
    def _require_pin(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param(
                "rawasi_base.require_pin_on_issue", "True"
            )
            == "True"
        )

    def _open_pin_wizard(self, method):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "تأكيد بالـ PIN",
            "res_model": "rawasi.pin.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_method": method,
            },
        }

    def _notify(self, event):
        self.env["rawasi.notification.hook"].send(self, event)

    def _require_state(self, allowed):
        for rec in self:
            if rec.state not in allowed:
                label = dict(rec._fields["state"].selection).get(rec.state, rec.state)
                raise UserError("العملية غير مسموحة في الحالة الحالية: %s" % label)

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancelled"):
                raise UserError(
                    "لا يمكن حذف طلب مواد بعد بدء سير الاعتماد. استخدم «إلغاء»."
                )
        return super().unlink()
