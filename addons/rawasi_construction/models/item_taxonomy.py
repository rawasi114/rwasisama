# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


LEVEL_ORDER = {
    "division": 0,
    "section": 1,
    "category": 2,
    "subcategory": 3,
}
LEVEL_LABEL = dict(LEVEL_ORDER)  # filled below from the Selection


class ItemTaxonomy(models.Model):
    """عقدة في شجرة تصنيف البنود (4 مستويات: شعبة → قسم → فئة → فئة فرعية).

    قاعدة الترتيب صارمة: مستوى الابن = مستوى الأب + 1. الشعبة لا أب لها،
    والفئة الفرعية ورقة (لا أبناء، تستضيف البنود الكنسية).
    """

    _name = "rawasi.item.taxonomy"
    _description = "عقدة تصنيف بنود (Item Taxonomy Node)"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "code"
    _rec_name = "display_name_full"

    code = fields.Char(string="الكود", required=True, index=True)
    name_ar = fields.Char(string="الاسم العربي", required=True)
    name_en = fields.Char(string="Name (English)")

    parent_id = fields.Many2one(
        "rawasi.item.taxonomy", string="الأب",
        ondelete="restrict", index=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "rawasi.item.taxonomy", "parent_id", string="الأبناء"
    )

    level = fields.Selection(
        [
            ("division", "شعبة (Division)"),
            ("section", "قسم (Section)"),
            ("category", "فئة (Category)"),
            ("subcategory", "فئة فرعية (Sub-Category)"),
        ],
        required=True, index=True,
    )

    display_name_full = fields.Char(
        compute="_compute_display_name_full", store=True,
    )
    active = fields.Boolean(default=True)
    description = fields.Text()

    master_item_ids = fields.One2many(
        "rawasi.item.master", "taxonomy_id", string="البنود الكنسية"
    )
    master_item_count = fields.Integer(
        string="عدد البنود الكنسية", compute="_compute_master_item_count",
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)", "كود التصنيف يجب أن يكون فريداً.",
    )

    @api.depends("code", "name_ar", "parent_id.display_name_full")
    def _compute_display_name_full(self):
        for rec in self:
            label = "[%s] %s" % (rec.code or "", rec.name_ar or "")
            if rec.parent_id:
                rec.display_name_full = "%s / %s" % (
                    rec.parent_id.display_name_full or "", label,
                )
            else:
                rec.display_name_full = label

    @api.depends("master_item_ids")
    def _compute_master_item_count(self):
        for rec in self:
            rec.master_item_count = len(rec.master_item_ids)

    @api.constrains("parent_id", "level")
    def _check_hierarchy_consistency(self):
        for rec in self:
            my_idx = LEVEL_ORDER[rec.level]
            if rec.level == "division":
                if rec.parent_id:
                    raise ValidationError(_(
                        "الشعبة (division) لا يمكن أن يكون لها أب: %s"
                    ) % rec.display_name)
                continue
            if not rec.parent_id:
                raise ValidationError(_(
                    "هذا المستوى (%s) يجب أن يكون له أب."
                ) % rec.level)
            parent_idx = LEVEL_ORDER[rec.parent_id.level]
            if parent_idx != my_idx - 1:
                raise ValidationError(_(
                    "مستوى الابن (%s) يجب أن يكون أعمق من الأب (%s) بدرجة واحدة فقط."
                ) % (rec.level, rec.parent_id.level))

    @api.constrains("parent_id")
    def _check_no_recursion(self):
        if self._has_cycle("parent_id"):
            raise ValidationError(_("لا يمكن إنشاء حلقة في شجرة التصنيف."))

    def action_open_master_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("بنود التصنيف: %s") % self.display_name_full,
            "res_model": "rawasi.item.master",
            "view_mode": "list,form",
            "domain": [("taxonomy_id", "=", self.id)],
            "context": {"default_taxonomy_id": self.id},
        }
