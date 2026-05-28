# -*- coding: utf-8 -*-
"""سجل التتبع — كل قرار يربط نصاً أصلياً ببند مرجعي يُسجَّل هنا.

Append-only: نُنشئ صفّاً عن كل قرار (قبول، تعديل، رفض، إنشاء جديد)
ولا نُعدِّل لاحقاً. يصبح هذا السجل المادة الأولية لأي تحليل تاريخي للجودة
أو تدريب مستقبلي لمحرك المطابقة.
"""
from odoo import fields, models


class AuditTrail(models.Model):
    _name = "rawasi.audit.trail"
    _description = "سجل التتبع (Audit Trail)"
    _order = "decision_date desc"

    original_text = fields.Text(string="النص الأصلي", required=True)
    reference_item_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي المختار",
        ondelete="set null",
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
            ("exact_text",  "تطابق نصي كامل"),
            ("lcgpa_code",  "تطابق برمز LCGPA"),
            ("spec_pattern","تطابق بنمط المواصفات"),
            ("pgvector",    "تطابق دلالي pgvector"),
            ("manual",      "اختيار يدوي"),
        ],
        required=True, index=True, string="مصدر الترشيح",
    )
    confidence_score = fields.Float(string="درجة الثقة")
    user_action = fields.Selection(
        [
            ("accepted",       "قُبل الترشيح"),
            ("modified",       "عُدِّل الترشيح"),
            ("created_new",    "أُنشئ بند مرجعي جديد"),
            ("rejected",       "رُفض السطر بالكامل"),
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
        help="الدفعة التي صدر منها هذا القرار، إن كان من استيراد جماعي.",
    )
    notes = fields.Text(string="ملاحظات")
