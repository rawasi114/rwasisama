# -*- coding: utf-8 -*-
from odoo import fields, models


class RawasiWbsPhase(models.Model):
    _name = "rawasi.wbs.phase"
    _description = "مرحلة المشروع (قالب)"
    _order = "sequence, id"

    name = fields.Char(string="المرحلة", required=True, translate=True)
    code = fields.Char(string="الرمز")
    objective = fields.Text(string="الهدف المباشر", translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string="اللون")
    active = fields.Boolean(default=True)
    task_ids = fields.One2many(
        "rawasi.wbs.phase.task", "phase_id", string="المهام القياسية"
    )


class RawasiWbsPhaseTask(models.Model):
    _name = "rawasi.wbs.phase.task"
    _description = "مهمة قياسية ضمن مرحلة المشروع (قالب)"
    _order = "sequence, id"

    phase_id = fields.Many2one(
        "rawasi.wbs.phase", string="المرحلة", required=True, ondelete="cascade"
    )
    name = fields.Char(string="المهمة", required=True, translate=True)
    sequence = fields.Integer(default=10)
