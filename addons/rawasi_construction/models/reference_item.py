# -*- coding: utf-8 -*-
"""البند المرجعي — السجل المعتمَد لكل بند يتكرَّر في جداول الكميات."""
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


REFERENCE_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,4}-[A-Z]{2,4}-[A-Z0-9]{2,8}-\d{3}$"
)


class ReferenceItem(models.Model):
    _name = "rawasi.reference.item"
    _description = "بند مرجعي (Reference Item)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reference_code"
    _rec_name = "approved_name"

    reference_code = fields.Char(
        string="الرمز المرجعي", required=True, index=True, copy=False,
        help="نمط: XXX-XXX-XXXX-NNN — مثلاً FLR-POR-6060-001",
    )
    approved_name = fields.Char(
        string="الاسم المعتمد", required=True, index=True,
    )
    name_en = fields.Char(string="Name (English)")

    taxonomy_id = fields.Many2one(
        "rawasi.item.taxonomy", string="التصنيف", required=True, index=True,
        domain="[('level', '=', 'subcategory')]",
        help="البنود المرجعية تُربط بفئات فرعية فقط (أوراق شجرة التصنيف).",
    )
    uom_id = fields.Many2one(
        "uom.uom", string="وحدة القياس الافتراضية", required=True,
    )
    lcgpa_code_id = fields.Many2one(
        "rawasi.lcgpa.code", string="رمز LCGPA",
        help="رمز هيئة المحتوى المحلي والمشتريات الحكومية المرتبط بهذا البند.",
    )

    description_short = fields.Char(string="الوصف الموجز", size=255)
    description_long = fields.Html(string="الوصف التفصيلي")
    reference_image = fields.Binary(string="صورة مرجعية", attachment=True)

    # خصائص استراتيجية لرواسي
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
            ("import_wizard", "وصف اعتماد جديد"),
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
    specification_ids = fields.One2many(
        "rawasi.item.specification", "reference_item_id",
        string="المواصفات الفنية",
    )
    variant_ids = fields.One2many(
        "rawasi.item.variant", "reference_item_id",
        string="الصياغات البديلة",
    )
    variant_count = fields.Integer(
        string="عدد الصياغات",
        compute="_compute_variant_count", store=True,
    )

    # عمود embedding موجود من post_init_hook (vector(1024))

    _reference_code_uniq = models.Constraint(
        "UNIQUE(reference_code)",
        "الرمز المرجعي يجب أن يكون فريداً.",
    )

    @api.depends("variant_ids")
    def _compute_variant_count(self):
        for rec in self:
            rec.variant_count = len(rec.variant_ids)

    @api.constrains("reference_code")
    def _check_code_format(self):
        for rec in self:
            if not REFERENCE_CODE_PATTERN.match(rec.reference_code or ""):
                raise ValidationError(_(
                    "الرمز «%s» لا يتبع النمط المطلوب. مثال صحيح: FLR-POR-6060-001"
                ) % rec.reference_code)

    @api.constrains("taxonomy_id")
    def _check_taxonomy_is_subcategory(self):
        for rec in self:
            if rec.taxonomy_id.level != "subcategory":
                raise ValidationError(_(
                    "البند «%s» يجب أن يُربط بفئة فرعية، لكنه رُبط بمستوى «%s»."
                ) % (rec.approved_name, rec.taxonomy_id.level))

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
