# -*- coding: utf-8 -*-
"""دليل الاستخدام لورشة رواسي سما.

موديل قابل للتحرير من الواجهة يخدم:
  • دليل عام مُجمَّع حسب الدور (موظف ورشة / مدير عمليات)
  • دليل سير عمل لكل قائمة (العمليات، الميدانية، الجودة، التقارير، الإغلاق)
"""
from odoo import api, fields, models


MENU_SECTIONS = [
    ("overview", "نظرة عامة على الورشة"),
    ("operations", "العمليات"),
    ("field", "العمليات الميدانية"),
    ("quality", "الجودة والسلامة"),
    ("reports", "التقارير"),
    ("closeout", "المشاريع المغلقة"),
]


class WorkshopUserGuide(models.Model):
    _name = "rwasi.workshop.user.guide"
    _description = "دليل الاستخدام — Workshop User Guide"
    _order = "guide_type, sequence, id"

    name = fields.Char(string="العنوان", required=True, translate=True)
    subtitle = fields.Char(string="عنوان فرعي", translate=True)
    guide_type = fields.Selection(
        [("role", "حسب الدور"),
         ("workflow", "حسب سير العمل")],
        string="نوع الدليل", required=True, default="role",
    )
    role_group_id = fields.Many2one(
        "res.groups", string="الدور المستهدف",
    )
    menu_section_key = fields.Selection(
        MENU_SECTIONS, string="قسم القائمة",
    )
    sequence = fields.Integer(string="ترتيب", default=10)
    icon = fields.Char(
        string="أيقونة (FontAwesome)", default="fa-book",
    )
    color = fields.Integer(string="لون", default=0)
    content = fields.Html(
        string="المحتوى", translate=True, sanitize=True,
    )
    active = fields.Boolean(default=True)

    @api.depends("name", "guide_type", "role_group_id", "menu_section_key")
    def _compute_display_name(self):
        section_map = dict(MENU_SECTIONS)
        for rec in self:
            if rec.guide_type == "role" and rec.role_group_id:
                rec.display_name = f"{rec.role_group_id.name} — {rec.name}"
            elif rec.guide_type == "workflow" and rec.menu_section_key:
                rec.display_name = f"{section_map.get(rec.menu_section_key, '')} — {rec.name}"
            else:
                rec.display_name = rec.name or ""
