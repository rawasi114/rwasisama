# -*- coding: utf-8 -*-
"""المواصفة الفنية المُستخلَصة — Extracted Specification.

تُستخلَص تلقائياً بـ regex من وصف بند BOQ أو من السطر الخام:
الأبعاد، السماكة، القطر، الجهد، الدرجة، اللون، التشطيب...
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ExtractedSpecification(models.Model):
    _name = "rawasi.extracted.specification"
    _description = "مواصفة فنية مُستخلَصة — Extracted Specification"
    _order = "reference_item_id, display_order, id"

    reference_item_id = fields.Many2one(
        "rawasi.reference.item", required=True,
        ondelete="cascade", index=True, string="البند المرجعي",
    )
    spec_key = fields.Selection(
        [
            ("dimensions",   "الأبعاد"),
            ("thickness",    "السماكة"),
            ("diameter",     "القطر"),
            ("weight",       "الوزن"),
            ("strength",     "الجهد / المقاومة"),
            ("grade",        "الدرجة"),
            ("color",        "اللون"),
            ("finish",       "التشطيب"),
            ("origin",       "المنشأ"),
            ("model",        "الموديل"),
            ("standard",     "المعيار"),
            ("other",        "أخرى"),
        ],
        required=True, index=True, string="نوع المواصفة",
    )
    spec_key_custom = fields.Char(string="نوع مخصص")
    spec_value = fields.Char(string="القيمة", required=True)
    spec_unit = fields.Char(string="الوحدة")
    extracted_via_auto = fields.Boolean(
        string="مُستخلَصة تلقائياً", default=False,
    )
    is_searchable = fields.Boolean(default=True, index=True)
    display_order = fields.Integer(default=10)

    @api.constrains("spec_key", "spec_key_custom")
    def _check_custom_key(self):
        for rec in self:
            if rec.spec_key == "other" and not rec.spec_key_custom:
                raise ValidationError(_(
                    "حين يكون النوع «أخرى»، يجب تعبئة «نوع مخصص»."
                ))
            if rec.spec_key != "other" and rec.spec_key_custom:
                raise ValidationError(_(
                    "«نوع مخصص» لا يُستخدم إلا حين يكون النوع «أخرى»."
                ))
