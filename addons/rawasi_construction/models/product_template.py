# -*- coding: utf-8 -*-
"""توسعة product.template لتمييز منتجات المقاولات وربطها بالبنود المرجعية.

كل بند مرجعي (rawasi.reference.item) يقابل قالب منتج واحد في كتالوج
Odoo (product.template) — منتج واحد لكل مادة بشكل قاطع كي تبقى تحليلات
الأسعار والمخزون دقيقة بلا تكرار. عند تعديل البند المرجعي تتزامن البيانات
الأساسية للمنتج المرتبط (الاسم، الوحدة، المواصفات، الرموز).

المنتج يُنشأ تلقائياً عند:
- إنشاء بند مرجعي يدوياً
- اعتماد دفعة استيراد (لكل بند مرجعي مُنشأ حديثاً)

اختيار النوع consu (Storable) ليظهر في المخزون مع جميع تحركاته.
"""
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_construction = fields.Boolean(
        string="بند تشييدي",
        index=True,
        help="يميِّز المنتجات الخاصة بالموديول الإنشائي ضمن كتالوج المنتجات العام.",
    )
    construction_nature = fields.Selection(
        CONSTRUCTION_NATURE,
        string="طبيعة البند",
        help="تحدد كيف يُعامَل البند في الشراء/المخزون/المحاسبة:\n"
             "- مادة خام: يُخزَّن ويُستهلك.\n"
             "- بند تسليم: مكوّن من مواد عبر BoM.\n"
             "- خدمة: لا مخزون.\n"
             "- باطن: يُحرّك مسار subcontract.\n"
             "- ورشة: يُصنَّع داخلياً.",
    )
    sbc_code_id = fields.Many2one(
        "rawasi.sbc.code",
        string="رمز SBC",
        index=True,
    )
    rawasi_unit_id = fields.Many2one(
        "rawasi.unit",
        string="الوحدة الإنشائية",
        help="الوحدة كما تُكتب في كراسات الشروط. تنعكس على uom_id (وحدة Odoo القياسية).",
    )
    lcgpa_code = fields.Char(string="رمز LCGPA / القائمة الإلزامية", index=True)
    mandatory_local = fields.Selection(
        [("yes", "نعم"), ("no", "لا")],
        string="منتج من القائمة الإلزامية",
        default="no",
    )
    construction_category_text = fields.Char(
        string="الفئة (كما وردت)",
        help="الفئة الأصلية كما ظهرت في كراسة الشروط (لتوثيق المصدر).",
    )
    work_group = fields.Char(string="البند/المجموعة")
    specifications = fields.Text(string="المواصفات الفنية")

    @api.onchange("rawasi_unit_id")
    def _onchange_rawasi_unit_id(self):
        for tmpl in self:
            uom = tmpl.rawasi_unit_id and tmpl.rawasi_unit_id.uom_id
            if uom:
                tmpl.uom_id = uom
                tmpl.uom_po_id = uom

    @api.onchange("is_construction")
    def _onchange_is_construction(self):
        for tmpl in self:
            if tmpl.is_construction and not tmpl.construction_nature:
                tmpl.construction_nature = "material"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_construction") and vals.get("rawasi_unit_id") and not vals.get("uom_id"):
                unit = self.env["rawasi.unit"].browse(vals["rawasi_unit_id"])
                if unit.uom_id:
                    vals["uom_id"] = unit.uom_id.id
                    vals.setdefault("uom_po_id", unit.uom_id.id)
        return super().create(vals_list)
