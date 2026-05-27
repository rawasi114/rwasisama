from odoo import models, fields


class MasterItem(models.Model):
    _name = "rps.master.item"
    _description = "Master Item (Rawasi Pricing Intelligence)"
    _order = "code"

    name = fields.Char(string="اسم البند", required=True)
    code = fields.Char(string="رمز البند", required=True, index=True)
    backend_id = fields.Char(string="Backend UUID", index=True)
    default_unit = fields.Char(string="الوحدة", required=True)
    description = fields.Text(string="الوصف")
    usage_count = fields.Integer(string="مرات الاستخدام", readonly=True)
    is_active = fields.Boolean(default=True)
