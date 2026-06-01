# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    pin_code = fields.Char(
        string="PIN (6 أرقام)",
        size=6,
        copy=False,
        help="لتأكيد العمليات الحرجة (صرف المواد، التجاوز الإداري).",
    )

    @api.constrains("pin_code")
    def _check_pin_code(self):
        for user in self:
            if user.pin_code and not (user.pin_code.isdigit() and len(user.pin_code) == 6):
                raise ValidationError("الـ PIN يجب أن يكون 6 أرقام بالضبط.")

    def check_pin(self, pin):
        """يتحقق من تطابق الـ PIN للمستخدم الحالي."""
        self.ensure_one()
        return bool(self.pin_code) and self.pin_code == (pin or "")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["pin_code"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["pin_code"]
