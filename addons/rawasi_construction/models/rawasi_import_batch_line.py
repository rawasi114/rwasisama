# -*- coding: utf-8 -*-
"""السطر الخام من جدول الكميات + نتائج المطابقة والمراجعة."""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ImportBatchLine(models.Model):
    _name = "rawasi.import.batch.line"
    _description = "سطر جدول كميات مُستلَم — Import Batch Line"
    _order = "import_batch_id, line_number"

    import_batch_id = fields.Many2one(
        "rawasi.import.batch", string="دفعة الاستيراد",
        required=True, ondelete="cascade", index=True,
    )
    line_number = fields.Integer(string="رقم السطر", required=True)

    # ── السطر كما ورد بالضبط ─────────────────────────────────────
    original_text = fields.Text(string="الوصف كما ورد", required=True)
    original_unit = fields.Char(string="وحدة القياس كما وردت")
    original_quantity = fields.Char(string="الكمية كما وردت")
    original_main_category = fields.Char(string="الفئة الرئيسية كما وردت")
    original_item_group = fields.Char(string="البند كما ورد")
    original_simplified_desc = fields.Char(string="الوصف المبسط كما ورد")
    original_specifications = fields.Text(string="المواصفات كما وردت")
    original_construction_code = fields.Char(string="الرمز الإنشائي كما ورد")
    original_mandatory_local = fields.Char(string="الإلزامي محلي كما ورد")

    # ── ناتج التوحيد التلقائي (Auto-Normalization) ──────────────
    normalized_unit_code = fields.Selection(
        [("SQM","م²"), ("CBM","م³"), ("MTR","م.ط"), ("EA","عدد"), ("KG","كجم")],
        string="الوحدة المُوحَّدة",
    )
    detected_lcgpa_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA المُكتشَف",
    )

    # ── ناتج محرك المطابقة الذكية ───────────────────────────────
    suggested_match_id = fields.Many2one(
        "rawasi.reference.item", string="الترشيح المقترح",
    )
    suggestion_confidence = fields.Float(string="درجة الثقة %")
    suggestion_source = fields.Selection(
        [
            ("exact_text",   "تطابق نصي كامل"),
            ("lcgpa_code",   "تطابق برمز LCGPA"),
            ("spec_pattern", "تطابق بنمط المواصفات"),
            ("pgvector",     "تطابق دلالي pgvector"),
            ("none",         "لم يُعثَر على ترشيح"),
        ],
        string="مصدر الترشيح",
    )

    # ── المواصفات المُستخلَصة بـ regex من النص ─────────────────
    extracted_dimensions = fields.Char(string="الأبعاد المُستخلَصة")
    extracted_thickness  = fields.Char(string="السماكة المُستخلَصة")
    extracted_diameter   = fields.Char(string="القطر المُستخلَص")
    extracted_strength   = fields.Char(string="الجهد/المقاومة")

    # ── حالة المراجعة وقرار المستخدم ────────────────────────────
    review_status = fields.Selection(
        [
            ("pending",     "بانتظار المراجعة"),
            ("accepted",    "قُبل الترشيح"),
            ("modified",    "عُدِّل الترشيح"),
            ("created_new", "أُنشئ بند مرجعي جديد"),
            ("saved",       "محفوظ"),
            ("rejected",    "مرفوض"),
        ],
        default="pending", required=True, index=True,
        string="حالة المراجعة",
    )
    final_match_id = fields.Many2one(
        "rawasi.reference.item", string="البند المرجعي النهائي",
        help="ما اختاره المراجع (قد يختلف عن الترشيح المقترح).",
    )
    reviewer_notes = fields.Text(string="ملاحظات المراجع")

    # ── أزرار شاشة المراجعة ─────────────────────────────────────
    def action_accept(self):
        for line in self:
            if not line.suggested_match_id:
                raise UserError(_(
                    "لا يوجد ترشيح لقبوله. عدِّل أو ارفض السطر بدلاً من ذلك."
                ))
            line.write({
                "review_status": "accepted",
                "final_match_id": line.suggested_match_id.id,
            })

    def action_reject(self):
        for line in self:
            line.write({"review_status": "rejected", "final_match_id": False})

    @api.onchange("final_match_id")
    def _onchange_final_match(self):
        if (self.final_match_id
                and self.suggested_match_id
                and self.final_match_id != self.suggested_match_id):
            self.review_status = "modified"
        elif self.final_match_id and not self.suggested_match_id:
            self.review_status = "modified"

    def _build_boq_values(self, tender):
        """يبني قيم rawasi.boq.item جاهزة للإنشاء على المنافسة المعطاة."""
        self.ensure_one()
        # دمج الوصف من المستويات الثلاثة + النص الأصلي
        parts = []
        if self.original_main_category:
            parts.append(self.original_main_category)
        if self.original_item_group:
            parts.append(self.original_item_group)
        if self.original_simplified_desc:
            parts.append(self.original_simplified_desc)
        # الوصف الأصلي الكامل آخر شي
        if self.original_text:
            parts.append(self.original_text)
        full_name = "\n".join(parts) if parts else (self.original_text or "")

        try:
            qty = float((self.original_quantity or "0").replace(",", "").strip())
        except (ValueError, AttributeError):
            qty = 0.0

        return {
            "competition_id": tender.id,
            "sequence": self.line_number * 10 if self.line_number else 10,
            "serial": str(self.line_number) if self.line_number else False,
            "category": self.original_main_category or False,
            "work_group": self.original_item_group or False,
            "name": full_name,
            "specifications": self.original_specifications or False,
            "unit_text": self.original_unit or False,
            "quantity": qty,
            "construction_code": self.original_construction_code or False,
            "mandatory_local": (
                "yes" if (self.original_mandatory_local or "").strip().lower() in ("نعم","yes")
                else "no" if (self.original_mandatory_local or "").strip().lower() in ("لا","no")
                else False
            ),
        }
