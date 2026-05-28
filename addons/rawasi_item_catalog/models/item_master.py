# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


CANONICAL_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,4}-[A-Z]{2,4}-[A-Z0-9]{2,8}-\d{3}$"
)


class ItemMaster(models.Model):
    """البند المعياري — السجل المرجعي الموحَّد لكل بند يتكرَّر في جداول الكميات."""

    _name = "rawasi.item.master"
    _description = "بند معياري (Standard Item)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "canonical_code"
    _rec_name = "name_ar"

    canonical_code = fields.Char(
        string="الكود المعياري", required=True, index=True, copy=False,
        help="نمط: XXX-XXX-XXXX-NNN — مثلاً FLR-POR-6060-001",
    )
    name_ar = fields.Char(string="الاسم الموحَّد", required=True, index=True)
    name_en = fields.Char(string="Name (English)")

    taxonomy_id = fields.Many2one(
        "rawasi.item.taxonomy", string="التصنيف", required=True, index=True,
        domain="[('level', '=', 'subcategory')]",
        help="البنود المعيارية تُربط بفئات فرعية فقط (الأوراق في شجرة التصنيف).",
    )
    uom_id = fields.Many2one(
        "uom.uom", string="وحدة القياس الافتراضية", required=True,
    )

    description_short = fields.Char(string="الوصف الموجز", size=255)
    description_long = fields.Html(string="الوصف التفصيلي")
    reference_image = fields.Binary(string="صورة مرجعية", attachment=True)

    # خصائص رواسي الاستراتيجية
    is_in_house = fields.Boolean(string="يُصنَّع داخلياً", default=False, index=True)
    workshop_type = fields.Selection(
        [
            ("carpentry", "نجارة"),
            ("metalwork", "حدادة"),
            ("aluminum", "ألمنيوم"),
            ("cnc", "CNC"),
            ("none", "لا يُصنَّع داخلياً"),
        ],
        default="none", string="نوع الورشة",
    )

    # خصائص الإدارة
    active = fields.Boolean(default=True)
    created_via = fields.Selection(
        [
            ("manual", "إدخال يدوي"),
            ("ai_suggestion", "اقتراح AI مُعتمَد"),
            ("bulk_import", "استيراد جماعي"),
        ],
        default="manual", required=True, string="مصدر الإنشاء",
    )
    created_by_user_id = fields.Many2one(
        "res.users", string="أنشأه",
        default=lambda self: self.env.user, readonly=True,
    )
    review_status = fields.Selection(
        [
            ("draft", "مسودة"),
            ("reviewed", "مراجَع"),
            ("approved", "معتمَد"),
        ],
        default="draft", index=True, string="حالة المراجعة", tracking=True,
    )

    # علاقات
    attribute_ids = fields.One2many(
        "rawasi.item.attribute", "canonical_item_id", string="المواصفات الفنية",
    )
    synonym_ids = fields.One2many(
        "rawasi.item.synonym", "canonical_item_id", string="الصياغات البديلة",
    )
    synonym_count = fields.Integer(
        string="عدد الصياغات",
        compute="_compute_synonym_count", store=True,
    )

    # عمود embedding يُنشأ عبر post_init_hook كنوع pgvector(1024) — لا يُعرَّف هنا
    # لأن ORM لا يدعم vector نيتيف. النفاذ إليه عبر SQL مباشر في المرحلة القادمة.

    _canonical_code_uniq = models.Constraint(
        "UNIQUE(canonical_code)",
        "الكود المعياري يجب أن يكون فريداً.",
    )

    @api.depends("synonym_ids")
    def _compute_synonym_count(self):
        for rec in self:
            rec.synonym_count = len(rec.synonym_ids)

    @api.constrains("canonical_code")
    def _check_code_format(self):
        for rec in self:
            if not CANONICAL_CODE_PATTERN.match(rec.canonical_code or ""):
                raise ValidationError(_(
                    "الكود «%s» لا يتبع النمط المطلوب. مثال صحيح: FLR-POR-6060-001"
                ) % rec.canonical_code)

    @api.constrains("taxonomy_id")
    def _check_taxonomy_is_subcategory(self):
        for rec in self:
            if rec.taxonomy_id.level != "subcategory":
                raise ValidationError(_(
                    "البند «%s» يجب أن يُربط بفئة فرعية، لكنه رُبط بمستوى «%s»."
                ) % (rec.name_ar, rec.taxonomy_id.level))

    def action_open_synonyms(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("صياغات بديلة: %s") % self.name_ar,
            "res_model": "rawasi.item.synonym",
            "view_mode": "list,form",
            "domain": [("canonical_item_id", "=", self.id)],
            "context": {"default_canonical_item_id": self.id},
        }
