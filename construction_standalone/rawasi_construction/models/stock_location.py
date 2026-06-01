# -*- coding: utf-8 -*-
"""توسعة مواقع المخزون لدعم العهدة الهرمية: مشروع → مهندس موقع.

البنية المعتمَدة:
    WH/Stock
        └── المشاريع/
                └── <اسم المشروع>/
                        ├── المخزن الرئيسي للمشروع
                        └── عهدة المهندسين/
                                ├── <اسم المهندس A>
                                ├── <اسم المهندس B>
                                └── ...

المنطق:
- كل مشروع مقاولات (rawasi_is_construction=True) يحصل تلقائياً على موقع مخزن
  خاص به (rawasi_project_location_id).
- لكل مهندس موقع في المشروع، يُنشأ موقع عهدة مستقل
  (rawasi.engineer.custody).
- نقل المواد إلى/من العهدة يتم عبر stock.picking داخلية بدون أثر محاسبي
  (لأن الكل ضمن نفس company وضمن WIP/Stock Asset).
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_rawasi_project = fields.Boolean(
        string="موقع مشروع رواسي",
        help="موقع جذر يمثّل مشروعاً إنشائياً؛ تحته كل مواقع العهدة والتخزين الفرعية.",
    )
    is_rawasi_custody = fields.Boolean(
        string="عهدة مهندس",
        help="موقع يحتفظ به مهندس موقع كعهدة شخصية ضمن مشروع.",
    )
    rawasi_project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        ondelete="restrict",
        index=True,
        help="المشروع الذي ينتمي إليه هذا الموقع (للمشاريع أو لعُهد المهندسين).",
    )
    rawasi_custody_user_id = fields.Many2one(
        "res.users",
        string="المهندس صاحب العهدة",
        ondelete="restrict",
        index=True,
        help="مهندس الموقع المسؤول عن المواد في هذه العهدة.",
    )


class RawasiEngineerCustody(models.Model):
    """سجل ربط بين (مهندس، مشروع، موقع عهدة) — لتسهيل الاستعلام والإدارة."""

    _name = "rawasi.engineer.custody"
    _description = "عهدة مهندس موقع داخل مشروع"
    _rec_name = "display_name"

    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="المهندس",
        required=True,
        ondelete="restrict",
        index=True,
    )
    location_id = fields.Many2one(
        "stock.location",
        string="موقع العهدة",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        related="project_id.company_id",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)
    active = fields.Boolean(default=True)

    @api.constrains("project_id", "user_id", "active")
    def _check_unique_active(self):
        for rec in self.filtered("active"):
            dup = self.search([
                ("id", "!=", rec.id),
                ("project_id", "=", rec.project_id.id),
                ("user_id", "=", rec.user_id.id),
                ("active", "=", True),
            ], limit=1)
            if dup:
                raise UserError(_(
                    "يوجد عهدة نشطة بالفعل للمهندس %(u)s في المشروع %(p)s."
                ) % {"u": rec.user_id.name, "p": rec.project_id.name})

    @api.depends("project_id.name", "user_id.name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s — %s" % (
                rec.project_id.name or "", rec.user_id.name or "",
            )

    @api.model
    def _ensure_for(self, project, user):
        """يضمن وجود عهدة نشطة للمهندس في المشروع، ويُنشئها مع موقع المخزن عند اللزوم."""
        if not project.rawasi_is_construction or not user:
            return self.browse()
        existing = self.search([
            ("project_id", "=", project.id),
            ("user_id", "=", user.id),
            ("active", "=", True),
        ], limit=1)
        if existing:
            return existing
        project._ensure_rawasi_project_location()
        parent = project.rawasi_custody_root_location_id
        location = self.env["stock.location"].create({
            "name": user.name or _("عهدة"),
            "usage": "internal",
            "location_id": parent.id,
            "company_id": project.company_id.id or self.env.company.id,
            "is_rawasi_custody": True,
            "rawasi_project_id": project.id,
            "rawasi_custody_user_id": user.id,
        })
        return self.create({
            "project_id": project.id,
            "user_id": user.id,
            "location_id": location.id,
        })

    def action_open_inventory(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("جرد عهدة %s") % (self.user_id.name or ""),
            "res_model": "stock.quant",
            "view_mode": "list",
            "domain": [("location_id", "=", self.location_id.id)],
            "context": {"search_default_internal_loc": 1},
        }
