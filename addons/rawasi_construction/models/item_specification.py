# -*- coding: utf-8 -*-
"""المواصفات الفنية المُستخلَصة من وصف البند (أبعاد، سماكات، أقطار، إلخ.).

تُستخلَص تلقائياً عبر regex من النص الأصلي، أو تُضاف يدوياً.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ItemSpecification(models.Model):
    _name = "rawasi.item.specification"
    _description = "مواصفة فنية (Technical Specification)"
    _order = "reference_item_id, display_order, id"

    reference_item_id = fields.Many2one(
        "rawasi.reference.item", required=True,
        ondelete="cascade", index=True, string="البند المرجعي",
    )
    spec_key = fields.Selection(
        [
            ("dimensions", "الأبعاد"),
            ("thickness", "السماكة"),
            ("diameter", "القطر"),
            ("weight", "الوزن"),
            ("strength", "الجهد / المقاومة"),
            ("grade", "الدرجة"),
            ("color", "اللون"),
            ("finish", "التشطيب"),
            ("origin", "المنشأ"),
            ("model", "الموديل"),
            ("standard", "المعيار"),
            ("other", "أخرى"),
        ],
        required=True, index=True, string="نوع المواصفة",
    )
    spec_key_custom = fields.Char(
        string="نوع مخصص",
        help="يُستخدم فقط حين تكون قيمة النوع «أخرى».",
    )
    spec_value = fields.Char(string="القيمة", required=True)
    spec_unit = fields.Char(string="الوحدة")
    extracted_via_auto = fields.Boolean(
        string="مُستخلَصة تلقائياً", default=False,
        help="مؤشر إن كانت هذه المواصفة جاءت من المستخلص التلقائي.",
    )
    is_searchable = fields.Boolean(default=True, index=True, string="قابل للبحث")
    display_order = fields.Integer(default=10, string="ترتيب العرض")

    @api.constrains("spec_key", "spec_key_custom")
    def _check_custom_key_only_when_other(self):
        for rec in self:
            if rec.spec_key == "other" and not rec.spec_key_custom:
                raise ValidationError(_(
                    "حين يكون النوع «أخرى»، يجب تعبئة «نوع مخصص»."
                ))
            if rec.spec_key != "other" and rec.spec_key_custom:
                raise ValidationError(_(
                    "«نوع مخصص» لا يُستخدم إلا حين يكون النوع «أخرى»."
                ))
