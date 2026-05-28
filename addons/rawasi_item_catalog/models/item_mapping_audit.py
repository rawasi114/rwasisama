# -*- coding: utf-8 -*-
from odoo import fields, models


class ItemMappingAudit(models.Model):
    """سجل لكل عملية ربط بين نص خام وبند كنسي.

    Append-only تقريباً: نُنشئ صفّاً عن كل قرار (قبول، تعديل، رفض) ولا
    نُعدّل لاحقاً. يصبح هذا السجل المادة الأولية لأي تحليل تاريخي للجودة
    أو تدريب مستقبلي لنموذج اقتراح أفضل.

    ملاحظة معمارية: SPEC §4.5 يحتوي على `tender_id` يربط بـ rawasi.tender.
    ذلك الربط مؤجَّل لمرحلة تكامل لاحقة احتراماً لقرار «مستقل تماماً»
    في SPEC §0.3 — حين نربط، الحقل سيشير إلى `rawasi.competition`
    (تسمية موديل المنافسات الفعلية في هذا النظام).
    """

    _name = "rawasi.item.mapping.audit"
    _description = "سجل قرارات الربط (Mapping Decision Log)"
    _order = "mapping_date desc"

    raw_text = fields.Text(string="النص الخام", required=True)
    canonical_item_id = fields.Many2one(
        "rawasi.item.master", string="البند المعياري المختار",
        ondelete="set null",
    )
    mapped_by_user_id = fields.Many2one(
        "res.users", string="نفّذها",
        required=True, default=lambda self: self.env.user,
    )
    mapping_date = fields.Datetime(
        default=fields.Datetime.now, index=True, string="تاريخ الربط",
    )
    suggestion_source = fields.Selection(
        [
            ("pgvector", "بحث دلالي pgvector"),
            ("claude_api", "اقتراح Claude API"),
            ("manual", "إدخال يدوي"),
            ("exact_match", "تطابق نصي مباشر"),
        ],
        required=True, index=True, string="مصدر الاقتراح",
    )
    claude_confidence = fields.Float(string="ثقة Claude")
    pgvector_distance = fields.Float(string="المسافة الدلالية")
    user_action = fields.Selection(
        [
            ("accepted", "قُبل الاقتراح"),
            ("modified", "عُدِّل الاقتراح"),
            ("rejected_new_canonical", "رُفض وأُنشئ بند كنسي جديد"),
            ("rejected_no_match", "رُفض بلا بديل (للمراجعة)"),
        ],
        required=True, index=True, string="إجراء المستخدم",
    )
    original_suggestion_id = fields.Many2one(
        "rawasi.item.master", string="البند المقترح الأصلي",
        ondelete="set null",
        help="البند الذي اقترحه النظام قبل تعديل المستخدم — مفيد لتقييم الجودة.",
    )
    notes = fields.Text(string="ملاحظات")
