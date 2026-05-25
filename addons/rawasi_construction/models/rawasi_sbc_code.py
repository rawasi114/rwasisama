# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiSbcCode(models.Model):
    _name = "rawasi.sbc.code"
    _description = "رمز كود البناء السعودي (SBC)"
    _order = "code"

    code = fields.Char(string="الرمز", required=True)
    name = fields.Char(string="البند/الفصل", required=True, translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "رمز SBC يجب أن يكون فريداً."),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.code} - {rec.name}" if rec.code else rec.name

    @api.model
    def match_code(self, raw_code):
        """يطابق نص رمز خام (مثل '2002') مع سجل، أو يعيد سجلاً فارغاً."""
        if not raw_code:
            return self.browse()
        code = str(raw_code).strip()
        if not code or code == "غير محدد":
            return self.browse()
        return self.search([("code", "=", code)], limit=1)
