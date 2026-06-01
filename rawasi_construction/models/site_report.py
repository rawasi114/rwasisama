# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RawasiDsr(models.Model):
    """التقرير اليومي للموقع (DSR)."""

    _name = "rawasi.dsr"
    _description = "تقرير يومي للموقع — رواسي"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "report_date desc, id desc"

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True, default="جديد")
    project_id = fields.Many2one(
        "project.project",
        string="المشروع",
        required=True,
        domain="[('rawasi_is_construction', '=', True)]",
        index=True,
    )
    report_date = fields.Date(string="التاريخ", required=True, default=fields.Date.context_today)
    weather = fields.Selection(
        selection=[("clear", "صحو"), ("hot", "حار"), ("rain", "ممطر"), ("dusty", "غبار")],
        string="الطقس",
        default="clear",
    )
    progress_note = fields.Text(string="ملخص الإنجاز")
    manpower_line_ids = fields.One2many("rawasi.dsr.manpower", "dsr_id", string="العمالة")
    equipment_line_ids = fields.One2many("rawasi.dsr.equipment", "dsr_id", string="المعدات")
    material_line_ids = fields.One2many("rawasi.dsr.material", "dsr_id", string="المواد المستهلكة")
    total_manpower = fields.Integer(compute="_compute_totals", store=True, string="إجمالي العمالة")
    state = fields.Selection(
        selection=[("draft", "مسودة"), ("confirmed", "معتمد")],
        string="الحالة",
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="الشركة", default=lambda self: self.env.company.id
    )

    @api.depends("manpower_line_ids.quantity")
    def _compute_totals(self):
        for dsr in self:
            dsr.total_manpower = sum(dsr.manpower_line_ids.mapped("quantity"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "جديد":
                vals["name"] = self.env["ir.sequence"].next_by_code("rawasi.dsr") or "جديد"
        return super().create(vals_list)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_reset_draft(self):
        self.write({"state": "draft"})


class RawasiDsrManpower(models.Model):
    _name = "rawasi.dsr.manpower"
    _description = "عمالة التقرير اليومي"

    dsr_id = fields.Many2one("rawasi.dsr", required=True, ondelete="cascade")
    trade = fields.Char(string="التخصص", required=True)
    quantity = fields.Integer(string="العدد", default=1)
    note = fields.Char(string="ملاحظة")


class RawasiDsrEquipment(models.Model):
    _name = "rawasi.dsr.equipment"
    _description = "معدات التقرير اليومي"

    dsr_id = fields.Many2one("rawasi.dsr", required=True, ondelete="cascade")
    equipment_id = fields.Many2one("rawasi.equipment", string="المعدة")
    description = fields.Char(string="الوصف")
    hours = fields.Float(string="ساعات التشغيل")


class RawasiDsrMaterial(models.Model):
    _name = "rawasi.dsr.material"
    _description = "مواد التقرير اليومي"

    dsr_id = fields.Many2one("rawasi.dsr", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="المادة")
    description = fields.Char(string="الوصف")
    qty = fields.Float(string="الكمية المستهلكة")
    uom_id = fields.Many2one("uom.uom", string="الوحدة")
