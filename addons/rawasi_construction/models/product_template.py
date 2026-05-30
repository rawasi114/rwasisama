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
        string="منتج مقاولات", default=False, index=True,
        help="عند التفعيل يظهر المنتج ضمن كتالوج منتجات المقاولات "
             "ويُربط ببند مرجعي في سجل البنود الموحَّد.",
    )
    rawasi_reference_item_id = fields.Many2one(
        "rawasi.reference.item",
        string="البند المرجعي",
        ondelete="set null", index=True, copy=False,
        help="البند المرجعي الذي يمثّله هذا المنتج في سجل البنود الموحَّد.",
    )
    rawasi_unit_id = fields.Many2one(
        "rawasi.unit", string="وحدة المقاولات",
        help="الوحدة كما عُرِّفت في نظام رواسي (م³، م²، م.ط، …).",
    )
    rawasi_sbc_code_id = fields.Many2one(
        "rawasi.sbc.code", string="رمز SBC",
        help="كود البناء السعودي المرتبط بهذا المنتج.",
    )
    rawasi_lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        help="رمز هيئة المحتوى المحلي.",
    )
    rawasi_specifications = fields.Text(
        string="المواصفات الفنية",
        help="المواصفات الفنية كما وردت في البند المرجعي.",
    )
    rawasi_main_category = fields.Char(string="الفئة الرئيسية", index=True)
    rawasi_item_group = fields.Char(string="البند (المستوى الثاني)", index=True)

    @api.model
    def _create_for_reference_item(self, ref):
        """ينشئ قالب منتج مقاولات من بند مرجعي. مُسمَّى بحقول مفيدة جاهزة."""
        return self.create({
            "name": ref.approved_name,
            "is_construction": True,
            "type": "consu",
            "rawasi_reference_item_id": ref.id,
            "rawasi_unit_id": ref.default_uom_id.id if ref.default_uom_id else False,
            "rawasi_sbc_code_id": ref.sbc_code_id.id if ref.sbc_code_id else False,
            "rawasi_lcgpa_code_id": ref.lcgpa_code_id.id if ref.lcgpa_code_id else False,
            "rawasi_specifications": ref.description_short or False,
            "rawasi_main_category": ref.main_category or False,
            "rawasi_item_group": ref.item_group or False,
            "default_code": ref.reference_code,
        })

    def _sync_from_reference_item(self):
        """يُزامن بيانات المنتج مع البند المرجعي المرتبط."""
        for tmpl in self:
            ref = tmpl.rawasi_reference_item_id
            if not ref:
                continue
            tmpl.write({
                "name": ref.approved_name,
                "rawasi_unit_id": ref.default_uom_id.id if ref.default_uom_id else False,
                "rawasi_sbc_code_id": ref.sbc_code_id.id if ref.sbc_code_id else False,
                "rawasi_lcgpa_code_id": ref.lcgpa_code_id.id if ref.lcgpa_code_id else False,
                "rawasi_specifications": ref.description_short or False,
                "rawasi_main_category": ref.main_category or False,
                "rawasi_item_group": ref.item_group or False,
                "default_code": ref.reference_code,
            })
