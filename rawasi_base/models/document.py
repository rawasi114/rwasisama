# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiDocumentTag(models.Model):
    _name = "rawasi.document.tag"
    _description = "وسم وثيقة — رواسي"
    _order = "name"

    name = fields.Char(string="الوسم", required=True)
    color = fields.Integer(string="اللون")

    _sql_constraints = [
        ("name_uniq", "unique(name)", "اسم الوسم يجب أن يكون فريداً."),
    ]


class RawasiDocumentFolder(models.Model):
    _name = "rawasi.document.folder"
    _description = "مجلد وثائق — رواسي"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"

    name = fields.Char(string="الاسم", required=True)
    parent_id = fields.Many2one(
        "rawasi.document.folder", string="المجلد الأب", ondelete="cascade", index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(
        string="المسار الكامل", compute="_compute_complete_name", recursive=True, store=True
    )
    child_ids = fields.One2many("rawasi.document.folder", "parent_id", string="مجلدات فرعية")
    document_ids = fields.One2many("rawasi.document", "folder_id", string="الوثائق")
    document_count = fields.Integer(compute="_compute_document_count", string="عدد الوثائق")
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = "%s / %s" % (folder.parent_id.complete_name, folder.name)
            else:
                folder.complete_name = folder.name

    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)


class RawasiDocument(models.Model):
    _name = "rawasi.document"
    _description = "وثيقة — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="العنوان", required=True, tracking=True)
    folder_id = fields.Many2one(
        "rawasi.document.folder", string="المجلد", required=True, ondelete="cascade", tracking=True
    )
    file = fields.Binary(string="الملف", attachment=True, required=True)
    file_name = fields.Char(string="اسم الملف")
    version = fields.Char(string="الإصدار", default="1.0", tracking=True)
    parent_document_id = fields.Many2one("rawasi.document", string="الإصدار السابق")
    is_current_version = fields.Boolean(string="الإصدار الحالي", default=True)
    tag_ids = fields.Many2many("rawasi.document.tag", string="الوسوم")
    owner_user_id = fields.Many2one(
        "res.users", string="المالك", default=lambda self: self.env.user.id, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    def action_new_version(self):
        """ينشئ نسخة جديدة مرتبطة بالحالية ويعلّم القديمة كغير حالية."""
        self.ensure_one()
        self.is_current_version = False
        return {
            "type": "ir.actions.act_window",
            "res_model": "rawasi.document",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_name": self.name,
                "default_folder_id": self.folder_id.id,
                "default_parent_document_id": self.id,
                "default_tag_ids": [(6, 0, self.tag_ids.ids)],
            },
        }
