# -*- coding: utf-8 -*-
from odoo import fields, models


class RawasiWbsPhase(models.Model):
    _name = "rawasi.wbs.phase"
    _description = "مرحلة WBS (قالب)"
    _order = "sequence, id"

    name = fields.Char(string="المرحلة", required=True, translate=True)
    code = fields.Char(string="الرمز")
    sequence = fields.Integer(default=10)
    color = fields.Integer(string="اللون")
    active = fields.Boolean(default=True)
