# -*- coding: utf-8 -*-
"""سجل التتبع — Audit Trail.

Append-only: لكل قرار يربط نصاً خاماً ببند مرجعي (قبول، تعديل، رفض،
إنشاء جديد) يُسجَّل صف هنا ولا يُعدَّل لاحقاً.
"""
from odoo import fields, models


class AuditTrail(models.Model):
    _name = "rawasi.audit.trail"
    _description = "سجل التتبع — Audit Trail"
    _order = "decision_date desc"

    original_text = fields.Text(string="النص الأصلي", required=True)
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي (قديم)",
        ondelete="set null",
    )
    product_tmpl_id = fields.Many2one(
        "product.template", string="منتج المقاولات",
        ondelete="set null", index=True,
        domain="[('is_construction_item', '=', True)]",
    )
    decided_by_user_id = fields.Many2one(
        "res.users", string="نفّذ القرار",
        required=True, default=lambda self: self.env.user,
    )
    decision_date = fields.Datetime(
        default=fields.Datetime.now, index=True, string="تاريخ القرار",
    )
    match_source = fields.Selection(
        [
            ("exact_text",    "تطابق نصي كامل"),
            ("lcgpa_code",    "تطابق برمز LCGPA"),
            ("spec_pattern",  "تطابق بنمط المواصفات"),
            ("pgvector",      "تطابق دلالي pgvector"),
            ("manual",        "اختيار يدوي"),
            ("training_data", "بيانات تدريب (استيراد القاعدة الموحَّدة)"),
            ("none",          "لم يُعثَر على ترشيح"),
        ],
        required=True, index=True, string="مصدر الترشيح",
    )
    confidence_score = fields.Float(string="درجة الثقة %")
    user_action = fields.Selection(
        [
            ("accepted",     "قُبل الترشيح"),
            ("modified",     "عُدِّل الترشيح"),
            ("created_new",  "أُنشئ بند مرجعي جديد"),
            ("rejected",     "رُفض السطر"),
            ("saved_no_match","حُفظ بلا ترشيح"),
        ],
        required=True, index=True, string="إجراء المستخدم",
    )
    original_suggestion_id = fields.Many2one(
        "rawasi.reference.item", string="الترشيح الأصلي قبل التعديل",
        ondelete="set null",
    )
    import_batch_id = fields.Many2one(
        "rawasi.import.batch", string="دفعة الاستيراد",
        ondelete="set null", index=True,
    )
    linked_tender_id = fields.Many2one(
        "rawasi.competition", string="المنافسة المرتبطة",
        ondelete="set null", index=True,
    )
    notes = fields.Text(string="ملاحظات")
