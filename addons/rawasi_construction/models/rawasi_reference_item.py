# -*- coding: utf-8 -*-
"""البند المرجعي — سجل البنود المرجعي (Reference Items Registry).

الكيان المركزي لمنظومة المطابقة الذكية. كل بند في BOQ يربط ببند مرجعي
واحد عبر `boq_item.reference_item_id`، وكل صياغة خام من ملفات اعتماد
تربط ببند مرجعي عبر `item_variant`.

الهرمية الرباعية مأخوذة من قالب اعتماد الفعلي:
  1. main_category    — الفئة الرئيسية
  2. item_group       — البند (المستوى الثاني)
  3. simplified_desc  — الوصف المبسط (المستوى الثالث)
  4. approved_name    — الاسم المعتمد (المختصر للعرض)
"""
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


REFERENCE_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,4}-[A-Z]{2,4}-[A-Z0-9]{2,8}-\d{3}$"
)


class ReferenceItem(models.Model):
    _name = "rawasi.reference.item"
    _description = "بند مرجعي — Reference Item"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "main_category, item_group, reference_code"
    _rec_name = "approved_name"

    reference_code = fields.Char(
        string="الرمز المرجعي", required=True, index=True, copy=False,
        help="نمط: XXX-XXX-XXXX-NNN — مثلاً FLR-POR-6060-001",
    )
    approved_name = fields.Char(
        string="الاسم المعتمد", required=True, index=True, tracking=True,
    )
    name_en = fields.Char(string="Name (English)")

    # ── الهرمية الرباعية كما في قالب اعتماد ─────────────────────
    main_category = fields.Char(
        string="الفئة الرئيسية", required=True, index=True, tracking=True,
        help="المستوى الأول — مثلاً «الأعمال الإنشائية» أو «أعمال التشطيبات والعزل».",
    )
    item_group = fields.Char(
        string="البند (المستوى الثاني)", required=True, index=True,
        help="مثلاً «أعمال الحفر والردم» أو «الخرسانة المصبوبة بالموقع».",
    )
    simplified_desc = fields.Char(
        string="الوصف المبسط (المستوى الثالث)",
        help="مثلاً «حفر للأساسات والميدات» أو «خرسانة أرضيات».",
    )

    # ── الربط بالكيانات الأخرى ───────────────────────────────────
    lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        help="رمز هيئة المحتوى المحلي المرتبط بالبند.",
    )
    sbc_code_id = fields.Many2one(
        "rawasi.sbc.code", string="رمز SBC (كود البناء السعودي)",
    )
    default_uom_id = fields.Many2one(
        "rawasi.unit", string="وحدة القياس الافتراضية",
    )

    # ── الوصف الكامل والمواصفات ─────────────────────────────────
    description_short = fields.Char(string="وصف موجز", size=255)
    description_long = fields.Html(string="وصف تفصيلي")
    reference_image = fields.Binary(string="صورة مرجعية", attachment=True)

    # ── المواصفات الفنية المُستخلَصة ────────────────────────────
    extracted_specification_ids = fields.One2many(
        "rawasi.extracted.specification", "reference_item_id",
        string="المواصفات المُستخلَصة",
    )

    # ── الصياغات البديلة ─────────────────────────────────────────
    item_variant_ids = fields.One2many(
        "rawasi.item.variant", "reference_item_id",
        string="الصياغات البديلة",
    )
    variant_count = fields.Integer(
        compute="_compute_variant_count", store=True,
        string="عدد الصياغات",
    )

    # ── خصائص استراتيجية ────────────────────────────────────────
    is_in_house = fields.Boolean(
        string="يُصنَّع داخلياً", default=False, index=True,
    )
    workshop_type = fields.Selection(
        [
            ("carpentry", "نجارة"),
            ("metalwork", "حدادة"),
            ("aluminum",  "ألمنيوم"),
            ("cnc",       "CNC"),
            ("none",      "لا يُصنَّع داخلياً"),
        ],
        default="none", string="نوع الورشة",
    )

    # ── الإدارة ─────────────────────────────────────────────────
    active = fields.Boolean(default=True)
    created_via = fields.Selection(
        [
            ("manual",         "إدخال يدوي"),
            ("import_wizard",  "معالج الاستيراد"),
            ("bulk_import",    "استيراد جماعي"),
        ],
        default="manual", required=True, string="مصدر الإنشاء",
    )
    review_status = fields.Selection(
        [
            ("draft",    "مسودة"),
            ("reviewed", "مراجَع"),
            ("approved", "معتمَد"),
        ],
        default="draft", index=True, tracking=True,
        string="حالة المراجعة",
    )

    _reference_code_uniq = models.Constraint(
        "UNIQUE(reference_code)",
        "الرمز المرجعي يجب أن يكون فريداً.",
    )

    @api.depends("item_variant_ids")
    def _compute_variant_count(self):
        for rec in self:
            rec.variant_count = len(rec.item_variant_ids)

    @api.constrains("reference_code")
    def _check_code_format(self):
        for rec in self:
            if not REFERENCE_CODE_PATTERN.match(rec.reference_code or ""):
                raise ValidationError(_(
                    "الرمز «%s» لا يتبع النمط المطلوب. مثال صحيح: FLR-POR-6060-001"
                ) % rec.reference_code)

    def action_open_variants(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("الصياغات البديلة: %s") % self.approved_name,
            "res_model": "rawasi.item.variant",
            "view_mode": "list,form",
            "domain": [("reference_item_id", "=", self.id)],
            "context": {"default_reference_item_id": self.id},
        }
