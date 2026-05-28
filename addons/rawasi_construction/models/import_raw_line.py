# -*- coding: utf-8 -*-
"""السطر الخام — كل صف من ملف Excel يُخزَّن كما ورد بالضبط، مع نتيجة
ترشيح محرك المطابقة وحالة مراجعة المستخدم.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .arabic_utils import normalize_text


class ImportRawLine(models.Model):
    _name = "rawasi.import.raw.line"
    _description = "سطر خام من جدول كميات (Raw Import Line)"
    _order = "batch_id, line_number"

    batch_id = fields.Many2one(
        "rawasi.import.batch", string="دفعة الاستيراد",
        required=True, ondelete="cascade", index=True,
    )
    line_number = fields.Integer(string="رقم السطر", required=True)

    # ── النص كما ورد بالضبط (لا تعديل) ─────────────────────────
    original_text = fields.Text(string="الوصف كما ورد", required=True)
    original_unit = fields.Char(string="وحدة القياس كما وردت")
    original_quantity = fields.Char(string="الكمية كما وردت")
    original_category = fields.Char(string="الفئة كما وردت")
    original_item_group = fields.Char(string="البند كما ورد")
    original_specs = fields.Text(string="المواصفات كما وردت")
    original_lcgpa_raw = fields.Char(string="رمز LCGPA كما ورد")
    original_mandatory_local = fields.Char(string="منتج إلزامي محلي كما ورد")

    # ── النواتج المُوحَّدة ─────────────────────────────────────
    normalized_unit_id = fields.Many2one(
        "uom.uom", string="الوحدة المُوحَّدة",
        help="ناتج مُوحِّد وحدات القياس (الـ 13 صياغة → 5 وحدات معتمدة).",
    )
    detected_lcgpa_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA المُكتشَف",
    )

    # ── ناتج محرك المطابقة ───────────────────────────────────────
    suggested_match_id = fields.Many2one(
        "rawasi.reference.item", string="الترشيح المقترح",
        help="ناتج محرك المطابقة الرباعي المستويات.",
    )
    suggestion_confidence = fields.Float(
        string="درجة الثقة %",
        help="من 0 إلى 100 — نسبة يقين الترشيح.",
    )
    suggestion_source = fields.Selection(
        [
            ("exact_text",  "تطابق نصي كامل"),
            ("lcgpa_code",  "تطابق برمز LCGPA"),
            ("spec_pattern","تطابق بنمط المواصفات"),
            ("pgvector",    "تطابق دلالي pgvector"),
            ("none",        "لم يُعثَر على ترشيح"),
        ],
        string="مصدر الترشيح",
    )

    # ── المواصفات المُستخلَصة (regex على original_text) ──────────
    extracted_dimensions = fields.Char(string="الأبعاد المُستخلَصة")
    extracted_thickness  = fields.Char(string="السماكة المُستخلَصة")
    extracted_diameter   = fields.Char(string="القطر المُستخلَص")
    extracted_strength   = fields.Char(string="الجهد / المقاومة")

    # ── حالة المراجعة وقرار المستخدم ───────────────────────────
    review_status = fields.Selection(
        [
            ("pending",     "بانتظار المراجعة"),
            ("accepted",    "قُبل الترشيح"),
            ("modified",    "عُدِّل الترشيح"),
            ("created_new", "أُنشئ بند مرجعي جديد"),
            ("rejected",    "رُفض"),
        ],
        default="pending", required=True, index=True,
        string="حالة المراجعة", tracking=True,
    )
    final_match_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي النهائي",
        help="الذي اختاره المستخدم في المراجعة (قد يختلف عن الترشيح).",
    )
    reviewer_notes = fields.Text(string="ملاحظات المراجع")

    # ── أزرار شاشة المراجعة ───────────────────────────────────
    def action_accept(self):
        for line in self:
            if not line.suggested_match_id:
                raise UserError(_(
                    "لا يوجد ترشيح لقبوله. عدِّل أو ارفض السطر بدلاً من ذلك."
                ))
            line.review_status = "accepted"
            line.final_match_id = line.suggested_match_id

    def action_reject(self):
        for line in self:
            line.review_status = "rejected"
            line.final_match_id = False

    def action_modify(self):
        """يفتح نافذة لاختيار بند مرجعي بديل."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("تعديل الترشيح"),
            "res_model": "rawasi.import.raw.line",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": {"default_review_status": "modified"},
        }

    @api.onchange("final_match_id")
    def _onchange_final_match(self):
        if self.final_match_id and self.final_match_id != self.suggested_match_id:
            self.review_status = "modified"

    def _normalized_original(self):
        self.ensure_one()
        return normalize_text(self.original_text or "")
