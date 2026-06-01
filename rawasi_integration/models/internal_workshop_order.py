# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class RawasiInternalWorkshopOrder(models.Model):
    """أمر التصنيع الداخلي — يربط طلب مواد مقاولات بأمر تصنيع ورشة.

    السيناريو الذهبي: بند BoQ بمسار «تصنيع داخلي» يُصنَّع في الورشة بدل الشراء
    الخارجي، عبر أمر بيع داخلي بين الشركة ونفسها، مع تحليل تكلفة مزدوج.
    """

    _name = "rawasi.internal.workshop.order"
    _description = "أمر تصنيع داخلي — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="المرجع", required=True, copy=False, readonly=True, default="جديد", index=True
    )
    construction_mr_id = fields.Many2one(
        "rawasi.material.request", string="طلب مواد المقاولات", required=True, ondelete="cascade"
    )
    project_id = fields.Many2one(
        related="construction_mr_id.project_id", string="المشروع", store=True
    )
    boq_item_id = fields.Many2one(
        related="construction_mr_id.boq_item_id", string="بند جدول الكميات", store=True
    )
    reference_item_id = fields.Many2one(
        related="boq_item_id.reference_item_id", string="البند المرجعي", store=True
    )
    product_id = fields.Many2one(
        related="reference_item_id.product_id", string="المنتج", store=True
    )
    section_id = fields.Many2one(
        "rawasi.workshop.section", string="قسم التصنيع", required=True
    )
    qty = fields.Float(string="الكمية", default=1.0, required=True)
    cost_estimate = fields.Monetary(
        string="التكلفة التقديرية", currency_field="currency_id"
    )
    margin_pct = fields.Selection(
        selection=[("0", "سعر التكلفة (0%)"), ("5", "التكلفة + 5% هامش مخاطر")],
        string="الهامش",
        default="5",
        required=True,
    )
    final_price = fields.Monetary(
        compute="_compute_final_price", store=True, string="سعر البيع الداخلي",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    sale_order_id = fields.Many2one("sale.order", string="أمر البيع الداخلي", readonly=True, copy=False)
    workshop_mo_id = fields.Many2one("rawasi.workshop.mo", string="أمر التصنيع", readonly=True, copy=False)
    is_internal = fields.Boolean(default=True, readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "مسودة"),
            ("sale_pending", "بانتظار اعتماد الحسابات"),
            ("confirmed", "أمر بيع معتمد"),
            ("in_production", "قيد التصنيع"),
            ("delivered_to_project", "سُلِّم للمشروع"),
            ("cancelled", "ملغى"),
        ],
        string="الحالة",
        default="draft",
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("cost_estimate", "margin_pct")
    def _compute_final_price(self):
        for order in self:
            factor = 1.0 + (float(order.margin_pct or "0") / 100.0)
            order.final_price = order.cost_estimate * factor

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("rawasi.internal.workshop.order") or "جديد"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # إنشاء أمر البيع الداخلي
    # ------------------------------------------------------------------
    def action_create_sale_order(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError("أمر البيع أُنشئ بالفعل.")
        if not self.product_id:
            raise UserError("البند المرجعي لا يملك منتجاً مرتبطاً.")
        partner = self.env.ref("rawasi_integration.partner_internal_construction")
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "is_internal_workshop": True,
                "internal_workshop_order_id": self.id,
                "origin": self.name,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_id.id,
                            "product_uom_qty": self.qty,
                            "price_unit": self.final_price / self.qty if self.qty else self.final_price,
                            "name": self.product_id.display_name,
                        },
                    )
                ],
            }
        )
        self.write({"sale_order_id": so.id, "state": "sale_pending"})
        self.env["rawasi.notification.hook"].send(self, "internal_so_created")
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": so.id,
            "view_mode": "form",
        }

    def _action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "تصنيع داخلي بالورشة",
            "res_model": "rawasi.internal.workshop.order",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
        }

    def action_view_workshop_mo(self):
        self.ensure_one()
        if not self.workshop_mo_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "rawasi.workshop.mo",
            "res_id": self.workshop_mo_id.id,
            "view_mode": "form",
        }
