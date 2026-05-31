# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiReferenceItem(models.Model):
    """البند المرجعي — الكتالوج المركزي للبنود (نواة النظام).

    كل بند في جداول الكميات يرتبط ببند مرجعي واحد، ويرتبط كل بند مرجعي
    بمنتج مخزون واحد. حقل procurement_type يحدد مسار التوريد، ومنه
    in_house_workshop الذي يفعّل سيناريو التصنيع الداخلي (المرحلة 7).
    """

    _name = "rawasi.reference.item"
    _description = "بند مرجعي — رواسي"
    _inherit = ["mail.thread"]
    _order = "code, name"

    name = fields.Char(string="الاسم", required=True, tracking=True, index=True)
    code = fields.Char(
        string="الرمز",
        copy=False,
        index=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("rawasi.reference.item") or "/",
    )
    category = fields.Selection(
        selection=[
            ("civil", "أعمال إنشائية ومدنية"),
            ("electrical", "كهرباء"),
            ("plumbing", "سباكة"),
            ("hvac", "تكييف وتهوية"),
            ("finishing", "تشطيبات"),
            ("carpentry", "نجارة"),
            ("steel", "حدادة ومعادن"),
            ("aluminum", "ألمنيوم"),
            ("site", "مستلزمات موقع"),
            ("other", "أخرى"),
        ],
        string="التصنيف",
        default="other",
        required=True,
        tracking=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="وحدة القياس",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    standard_cost = fields.Monetary(string="التكلفة المعيارية", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    procurement_type = fields.Selection(
        selection=[
            ("purchase", "شراء خارجي"),
            ("in_house_workshop", "تصنيع داخلي بالورشة"),
            ("subcontract", "مقاول باطن"),
        ],
        string="مسار التوريد",
        default="purchase",
        required=True,
        tracking=True,
        help="«تصنيع داخلي بالورشة» يفعّل إنشاء أمر بيع داخلي للورشة بدل الشراء.",
    )
    specification = fields.Text(string="المواصفات")
    product_id = fields.Many2one(
        "product.product", string="منتج المخزون", copy=False, tracking=True
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "رمز البند المرجعي يجب أن يكون فريداً.",
    )

    # ------------------------------------------------------------------
    # تزامن المنتج: كل بند مرجعي ← منتج مخزون واحد
    # ------------------------------------------------------------------
    def _prepare_product_vals(self):
        self.ensure_one()
        return {
            "name": self.name,
            "type": "consu",
            "is_storable": True,
            "uom_id": self.uom_id.id,
            "uom_po_id": self.uom_id.id,
            "standard_price": self.standard_cost,
            "default_code": self.code,
            "rawasi_reference_item_id": self.id,
            "purchase_ok": self.procurement_type == "purchase",
        }

    def _sync_product(self):
        for item in self:
            if item.product_id:
                item.product_id.write(
                    {
                        "name": item.name,
                        "standard_price": item.standard_cost,
                        "uom_id": item.uom_id.id,
                        "uom_po_id": item.uom_id.id,
                        "purchase_ok": item.procurement_type == "purchase",
                    }
                )
            else:
                product = self.env["product.product"].create(item._prepare_product_vals())
                item.product_id = product.id

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        items._sync_product()
        return items

    def write(self, vals):
        res = super().write(vals)
        if {"name", "standard_cost", "uom_id", "procurement_type"} & set(vals):
            self._sync_product()
        return res
