# -*- coding: utf-8 -*-
"""سجل تدقيق الاستيراد الخفيف — صف واحد لكل سطر استيراد تمت مراجعته.

يسجّل ما اقترحه المحرك، وما قرّره المراجع، والبند المرجعي النهائي، فتبقى كل
قرارات الاستيراد قابلة للتتبّع.
"""
from odoo import fields, models


class RawasiImportAudit(models.Model):
    _name = "rawasi.import.audit"
    _description = "سجل تدقيق الاستيراد"
    _order = "create_date desc, id desc"

    original_text = fields.Text(string="النص الأصلي")
    reference_item_id = fields.Many2one("rawasi.reference.item", string="البند المرجعي النهائي")
    suggested_item_id = fields.Many2one("rawasi.reference.item", string="الترشيح المقترح")
    match_source = fields.Selection(
        [
            ("exact_text", "تطابق نصي كامل"),
            ("lcgpa_code", "تطابق برمز LCGPA"),
            ("fuzzy", "تطابق تقريبي"),
            ("none", "بلا ترشيح"),
            ("manual", "اختيار يدوي"),
        ],
        string="مصدر الترشيح",
    )
    confidence_score = fields.Float(string="درجة الثقة %")
    user_action = fields.Selection(
        [
            ("accepted", "قُبل الترشيح"),
            ("modified", "عُدِّل الترشيح"),
            ("saved_no_match", "حُفظ بلا ترشيح"),
            ("rejected", "مرفوض"),
        ],
        string="قرار المراجع",
    )
    import_batch_id = fields.Many2one("rawasi.import.batch", string="دفعة الاستيراد", ondelete="cascade")
    competition_id = fields.Many2one("rawasi.competition", string="المنافسة")
    user_id = fields.Many2one("res.users", string="المراجع", default=lambda self: self.env.user)
