# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiMaterialRequest(models.Model):
    _name = "rawasi.material.request"
    _description = "طلب مواد (Material Request)"
    _inherit = ["mail.thread", "mail.activity.mixin", "rawasi.workflow.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="الرقم", required=True, copy=False, readonly=True, default="/")
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    request_date = fields.Date(string="التاريخ", default=fields.Date.context_today, tracking=True)
    requested_by_id = fields.Many2one(
        "res.users", string="مقدّم الطلب", default=lambda self: self.env.user
    )
    state = fields.Selection(
        [
            ("draft", "مسودة"),
            ("submitted", "مقدَّم"),
            ("approved", "معتمد"),
            ("procured", "تم الشراء"),
            ("rejected", "مرفوض"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "rawasi.material.request.line", "request_id", string="السطور"
    )
    note = fields.Text(string="ملاحظات")
    override_budget = fields.Boolean(
        string="تجاوز الميزانية معتمد", readonly=True, copy=False, tracking=True
    )
    has_over_budget = fields.Boolean(compute="_compute_budget_flags", store=True)
    has_locked_item = fields.Boolean(compute="_compute_budget_flags", store=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount_total = fields.Monetary(string="الإجمالي", compute="_compute_amount_total", store=True)
    # ربط بـ RFQ القياسي (purchase.order) المُنشأ تلقائياً عند الـ submit
    purchase_order_id = fields.Many2one(
        "purchase.order", string="RFQ المشتريات",
        readonly=True, copy=False, tracking=True,
        help="طلب عرض الأسعار في موديول المشتريات؛ يُنشأ تلقائياً عند رفع الطلب.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.material.request"
                ) or "/"
        return super().create(vals_list)

    @api.depends("line_ids.amount_subtotal")
    def _compute_amount_total(self):
        for mr in self:
            mr.amount_total = sum(mr.line_ids.mapped("amount_subtotal"))

    @api.depends("line_ids.over_budget", "line_ids.boq_item_id.is_locked")
    def _compute_budget_flags(self):
        for mr in self:
            mr.has_over_budget = any(mr.line_ids.mapped("over_budget"))
            mr.has_locked_item = any(mr.line_ids.mapped("boq_item_id.is_locked"))

    # ── سير العمل + فحص الميزانية ────────────────────────────────
    def action_submit(self):
        """يرفع الطلب لاعتماد المكتب الفني + ينشئ RFQ مسودة في المشتريات
        تلقائياً ليبدأ قسم المشتريات جمع عروض الأسعار بالتوازي."""
        for mr in self:
            if not mr.line_ids:
                raise UserError(_("لا يمكن تقديم طلب بلا سطور."))
            mr.state = "submitted"
            mr._ensure_rfq_draft()

    def _ensure_rfq_draft(self):
        """ينشئ RFQ مسودة في purchase.order إن لم يوجد، أو يعيد فتح
        أحدث RFQ ملغى من نفس MR (للتدفقات إعادة الرفع بعد الرفض)."""
        self.ensure_one()
        PO = self.env["purchase.order"].sudo()

        # إن وُجد RFQ مرتبط ولا يزال draft/sent → استخدمه (idempotent)
        if self.purchase_order_id and self.purchase_order_id.state in ("draft", "sent"):
            return self.purchase_order_id

        partner = self.env.ref(
            "rawasi_construction.partner_tbd_vendor", raise_if_not_found=False
        )
        if not partner:
            raise UserError(_(
                "لم يُعثر على جهة المورّد الافتراضية (rawasi_construction."
                "partner_tbd_vendor). تواصل مع الأدمن."
            ))

        po_lines = []
        for line in self.line_ids:
            desc = (line.description or
                    (line.boq_item_id.name if line.boq_item_id else _("بند مواد")))
            project_ref = self.project_id.name or ""
            full_name = "[%s] %s" % (self.name, desc) if project_ref else desc
            po_lines.append((0, 0, {
                "name": full_name,
                "product_qty": line.quantity or 1.0,
                "price_unit": line.unit_cost or 0.0,
                "date_planned": fields.Datetime.now(),
            }))

        po = PO.create({
            "partner_id": partner.id,
            "origin": "%s / %s" % (self.name, self.project_id.name or ""),
            "rawasi_mr_id": self.id,
            "order_line": po_lines,
        })
        self.purchase_order_id = po.id
        po.message_post(body=_(
            "أُنشئ هذا الـ RFQ تلقائياً من طلب المواد %s (مشروع: %s). "
            "حدّد المورّد الفعلي بدلاً من «مورّد للتحديد» قبل التأكيد."
        ) % (self.name, self.project_id.name or "-"))
        self.message_post(body=_("تم إنشاء RFQ مسودة في المشتريات: %s") % po.name)
        return po

    def action_open_rfq(self):
        """يفتح الـ RFQ المرتبط في موديول المشتريات."""
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError(_("لا يوجد RFQ مرتبط بهذا الطلب بعد."))
        return {
            "type": "ir.actions.act_window",
            "name": _("طلب عرض الأسعار"),
            "res_model": "purchase.order",
            "res_id": self.purchase_order_id.id,
            "view_mode": "form",
        }

    def _check_budget(self):
        """فحص الميزانية الآلي: يرفض التجاوز إلا إذا اعتُمد تجاوزٌ صريح."""
        for mr in self:
            locked = mr.line_ids.filtered(lambda l: l.boq_item_id.is_locked)
            if locked:
                raise UserError(
                    _("بنود مقفلة للطلبات: %s")
                    % ", ".join(locked.mapped("boq_item_id.name"))
                )
            if mr.has_over_budget and not mr.override_budget:
                raise UserError(
                    _(
                        "الطلب يتجاوز الميزانية المتبقية لبعض بنود جدول الكميات. "
                        "يلزم اعتماد «تجاوز الميزانية» من مدير المشاريع للمتابعة."
                    )
                )

    def action_approve(self):
        for mr in self:
            mr._check_budget()
            mr.state = "approved"
            if mr.override_budget:
                mr.message_post(
                    body=_("تمت الموافقة مع تجاوز الميزانية (BUDGET OVERRIDE)."),
                    subtype_xmlid="mail.mt_note",
                )

    def action_override_budget(self):
        """اعتماد تجاوز الميزانية — لمدير المشاريع/المدير العام فقط."""
        if not self.env.user.has_group("rawasi_construction.group_projects_director"):
            raise UserError(_("اعتماد تجاوز الميزانية يتطلب صلاحية مدير المشاريع."))
        for mr in self:
            mr.override_budget = True
            mr.message_post(body=_("تم اعتماد تجاوز الميزانية بواسطة %s") % self.env.user.name)

    def action_reject(self):
        """يرفض الطلب + يلغي RFQ المسودة المرتبطة (إن وُجدت ولم تُؤكَّد)."""
        for mr in self:
            mr.state = "rejected"
            po = mr.purchase_order_id
            if po and po.state in ("draft", "sent"):
                po.sudo().button_cancel()
                mr.message_post(body=_("أُلغي الـ RFQ المرتبط (%s) لرفض الطلب.")
                                % po.name)

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})

    def action_create_po(self):
        """ينشئ أمر شراء من طلب معتمد، ويضع الطلب في حالة «تم الشراء»."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("لا يمكن إنشاء أمر شراء إلا من طلب معتمد."))
        po = self.env["rawasi.purchase.order"].create({
            "project_id": self.project_id.id,
            "mr_id": self.id,
            "line_ids": [
                (0, 0, {
                    "boq_item_id": line.boq_item_id.id,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_cost": line.unit_cost,
                })
                for line in self.line_ids
            ],
        })
        self.state = "procured"
        return {
            "type": "ir.actions.act_window",
            "res_model": "rawasi.purchase.order",
            "res_id": po.id,
            "view_mode": "form",
        }


class RawasiMaterialRequestLine(models.Model):
    _name = "rawasi.material.request.line"
    _description = "سطر طلب مواد"

    request_id = fields.Many2one(
        "rawasi.material.request", required=True, ondelete="cascade"
    )
    request_state = fields.Selection(related="request_id.state", store=True)
    # القيد المعماري: كل سطر حركة يرتبط ببند BOQ
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند جدول الكميات", required=True
    )
    description = fields.Char(string="الوصف")
    quantity = fields.Float(string="الكمية", default=1.0)
    unit_id = fields.Many2one(related="boq_item_id.unit_id", string="الوحدة")
    unit_cost = fields.Monetary(string="تكلفة الوحدة")
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount_subtotal = fields.Monetary(
        string="الإجمالي", compute="_compute_subtotal", store=True
    )
    boq_remaining = fields.Monetary(
        string="المتبقي للبند", related="boq_item_id.amount_remaining"
    )
    over_budget = fields.Boolean(
        string="يتجاوز الميزانية", compute="_compute_over_budget", store=True
    )

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.amount_subtotal = line.quantity * line.unit_cost

    @api.depends("amount_subtotal", "boq_item_id.amount_remaining", "request_state")
    def _compute_over_budget(self):
        for line in self:
            # يُحتسب التجاوز قبل الاعتماد (المتبقي لا يشمل هذا السطر بعد)
            if line.request_state in ("draft", "submitted"):
                line.over_budget = line.amount_subtotal > line.boq_item_id.amount_remaining
            else:
                line.over_budget = False

    @api.onchange("boq_item_id")
    def _onchange_boq_item(self):
        if self.boq_item_id:
            self.unit_cost = self.boq_item_id.unit_cost
            self.description = self.boq_item_id.name
