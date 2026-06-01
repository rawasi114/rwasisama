# -*- coding: utf-8 -*-
"""الصياغة البديلة (Item Variant) — نص أصلي بديل يرتبط ببند مرجعي.

يتعلّم محرك المطابقة من عمليات الاستيراد المعتمدة: كل «نص أصلي» مقبول يُخزَّن هنا
(مطبَّعاً)، فعند ظهور الصياغة ذاتها لاحقاً تتطابق تطابقاً كاملاً. ويُتابِع حقل
«التكرار» كم مرة تكرّرت الصياغة.
"""
from odoo import api, fields, models

from .arabic_utils import normalize_match


class RawasiItemVariant(models.Model):
    _name = "rawasi.item.variant"
    _description = "صياغة بديلة لبند مرجعي"
    _order = "frequency desc, id desc"

    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي",
        required=True, ondelete="cascade", index=True,
    )
    original_text = fields.Text(string="النص الأصلي", required=True)
    normalized_text = fields.Char(string="النص المطبَّع", index=True)
    source_partner_id = fields.Many2one("res.partner", string="الجهة المصدر")
    frequency = fields.Integer(string="التكرار", default=1)
    last_seen_date = fields.Date(string="آخر ظهور", default=fields.Date.context_today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["normalized_text"] = normalize_match(vals.get("original_text", ""))
        return super().create(vals_list)

    def write(self, vals):
        if "original_text" in vals:
            vals["normalized_text"] = normalize_match(vals.get("original_text", ""))
        return super().write(vals)

    @api.model
    def learn(self, reference_item, original_text, source_partner=None):
        """يسجّل (أو يعزّز) صياغة بديلة لبند مرجعي."""
        if not reference_item or not original_text:
            return self.browse()
        normalized = normalize_match(original_text)
        existing = self.search(
            [
                ("reference_item_id", "=", reference_item.id),
                ("normalized_text", "=", normalized),
            ],
            limit=1,
        )
        if existing:
            existing.write(
                {
                    "frequency": existing.frequency + 1,
                    "last_seen_date": fields.Date.context_today(self),
                }
            )
            return existing
        return self.create(
            {
                "reference_item_id": reference_item.id,
                "original_text": original_text,
                "source_partner_id": source_partner.id if source_partner else False,
            }
        )
