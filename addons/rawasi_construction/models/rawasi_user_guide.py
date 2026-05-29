# -*- coding: utf-8 -*-
"""دليل الاستخدام — User Guide.

موديل قابل للتحرير من الواجهة (Html content) يخدم:
  • دليل عام مُجمَّع حسب الدور (guide_type='role')
  • دليل سير عمل لكل قائمة (guide_type='workflow')

الزر «دليل الاستخدام» داخل لوحة التحكم يفتح كل الأدلة،
وبنهاية كل قائمة (Procurement/Field/Contracts/...) بند يفتح
أدلّة هذا القسم تحديداً.
"""
from odoo import api, fields, models


MENU_SECTIONS = [
    ("overview", "نظرة عامة على النظام"),
    ("competitions", "المنافسات"),
    ("projects", "المشاريع"),
    ("reference_registry", "سجل البنود المرجعي"),
    ("price_intelligence", "رادار الترسية"),
    ("analytics", "لوحات وتحليلات"),
    ("wbs", "الجداول الزمنية (WBS)"),
    ("procurement", "المشتريات والميزانية"),
    ("field", "المستندات والموقع"),
    ("contracts", "العقود والمستحقات"),
    ("settings", "الإعدادات"),
]


class RawasiUserGuide(models.Model):
    _name = "rawasi.user.guide"
    _description = "دليل الاستخدام — Rawasi User Guide"
    _order = "guide_type, sequence, id"

    name = fields.Char(string="العنوان", required=True, translate=True)
    subtitle = fields.Char(string="عنوان فرعي", translate=True)
    guide_type = fields.Selection(
        [("role", "حسب الدور/التخصص"),
         ("workflow", "حسب سير العمل (قائمة)")],
        string="نوع الدليل", required=True, default="role",
    )
    role_group_id = fields.Many2one(
        "res.groups", string="الدور المستهدف",
        help="إلزامي إذا كان نوع الدليل «حسب الدور».",
    )
    menu_section_key = fields.Selection(
        MENU_SECTIONS, string="قسم القائمة",
        help="إلزامي إذا كان نوع الدليل «حسب سير العمل».",
    )
    sequence = fields.Integer(string="ترتيب", default=10)
    icon = fields.Char(
        string="أيقونة (FontAwesome)", default="fa-book",
        help="مثال: fa-hard-hat، fa-calculator، fa-cog",
    )
    color = fields.Integer(string="لون البطاقة", default=0)
    content = fields.Html(
        string="المحتوى", translate=True, sanitize=True,
        help="شرح وافٍ للدور أو سير العمل، يمكن استخدام صور وعناوين وقوائم.",
    )
    active = fields.Boolean(default=True)

    @api.depends("name", "guide_type", "role_group_id", "menu_section_key")
    def _compute_display_name(self):
        section_map = dict(MENU_SECTIONS)
        for rec in self:
            if rec.guide_type == "role" and rec.role_group_id:
                rec.display_name = f"{rec.role_group_id.name} — {rec.name}"
            elif rec.guide_type == "workflow" and rec.menu_section_key:
                section = section_map.get(rec.menu_section_key, "")
                rec.display_name = f"{section} — {rec.name}"
            else:
                rec.display_name = rec.name or ""
