# -*- coding: utf-8 -*-
"""الصياغة البديلة لبند مرجعي.

تتراكم من جداول الكميات الواردة من جهات حكومية مختلفة عبر منصة اعتماد.
كل صياغة تربط ببند مرجعي واحد، ولا تتكرَّر بصياغتها المُوحَّدة لنفس البند.
"""
from odoo import api, fields, models

from .arabic_utils import normalize_text


class ItemVariant(models.Model):
    _name = "rawasi.item.variant"
    _description = "صياغة بديلة (Item Variant)"
    _order = "frequency desc, last_seen_date desc"

    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي",
        required=True, ondelete="cascade", index=True,
    )
    original_text = fields.Char(
        string="الوصف كما ورد", required=True,
        help="النص الأصلي كما ورد في كراسة اعتماد، يحفظ بدون أي تعديل.",
    )
    normalized_text = fields.Char(
        string="النص المُوحَّد",
        compute="_compute_normalized", store=True, index=True,
    )
    source_entity_id = fields.Many2one(
        "res.partner", string="الجهة المصدر",
        help="الجهة الحكومية التي ظهرت هذه الصياغة في وثائقها (اختياري).",
    )
    frequency = fields.Integer(string="تكرار الظهور", default=1)
    first_seen_date = fields.Date(
        string="أول ظهور", default=fields.Date.context_today,
    )
    last_seen_date = fields.Date(
        string="آخر ظهور", default=fields.Date.context_today, index=True,
    )
    confidence_score = fields.Float(
        string="درجة الثقة", default=1.0,
        help="من 0 إلى 1 — مدى اليقين بالربط بالبند المرجعي.",
    )

    # عمود embedding موجود (vector(1024))

    _variant_uniq = models.Constraint(
        "UNIQUE(reference_item_id, normalized_text)",
        "لا يمكن تكرار نفس الصياغة المُوحَّدة لنفس البند المرجعي.",
    )

    @api.depends("original_text")
    def _compute_normalized(self):
        for rec in self:
            rec.normalized_text = normalize_text(rec.original_text or "")
