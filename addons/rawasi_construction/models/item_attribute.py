# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ItemAttribute(models.Model):
    """مواصفة فنية منظَّمة على بند معياري (مقاس / سماكة / درجة / لون...).

    الفصل عن `description_long` متعمَّد: المواصفات قابلة للاستعلام
    والتصفية، الوصف نص حر للعرض فقط.
    """

    _name = "rawasi.item.attribute"
    _description = "مواصفة فنية (Technical Specification)"
    _order = "canonical_item_id, display_order, id"

    canonical_item_id = fields.Many2one(
        "rawasi.item.master", required=True,
        ondelete="cascade", index=True, string="البند المعياري",
    )
    attribute_key = fields.Selection(
        [
            ("dimensions", "الأبعاد"),
            ("thickness", "السماكة"),
            ("weight", "الوزن"),
            ("grade", "الدرجة"),
            ("color", "اللون"),
            ("finish", "التشطيب"),
            ("origin", "المنشأ"),
            ("model", "الموديل"),
            ("standard", "المعيار"),
            ("other", "أخرى"),
        ],
        required=True, index=True, string="المفتاح",
    )
    attribute_key_custom = fields.Char(
        string="مفتاح مخصص",
        help="يُستخدم فقط حين تكون قيمة المفتاح «أخرى».",
    )
    attribute_value = fields.Char(string="القيمة", required=True)
    attribute_unit = fields.Char(string="الوحدة")
    is_searchable = fields.Boolean(default=True, index=True, string="قابل للبحث")
    display_order = fields.Integer(default=10, string="ترتيب العرض")

    @api.constrains("attribute_key", "attribute_key_custom")
    def _check_custom_key_only_when_other(self):
        for rec in self:
            if rec.attribute_key == "other" and not rec.attribute_key_custom:
                raise ValidationError(_(
                    "حين يكون المفتاح «أخرى»، يجب تعبئة «مفتاح مخصص»."
                ))
            if rec.attribute_key != "other" and rec.attribute_key_custom:
                raise ValidationError(_(
                    "«مفتاح مخصص» لا يُستخدم إلا حين يكون المفتاح «أخرى»."
                ))
