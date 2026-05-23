# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpSalesReport(models.Model):
    _name = 'simple.mrp.sales.report'
    _description = "تقرير مبيعات يومي"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New')
    sales_rep = fields.Char(string="المندوب")
    territory = fields.Char(string="المنطقة")
    date = fields.Date(string="التاريخ", default=fields.Date.context_today)
    reports_to = fields.Char(string="المشرف المباشر")
    visit_ids = fields.One2many(
        'simple.mrp.sales.report.visit', 'report_id', string="الزيارات")
    pipeline_ids = fields.One2many(
        'simple.mrp.sales.report.pipeline', 'report_id', string="الفرص")
    kpi_visits = fields.Integer(string="عدد الزيارات")
    kpi_new_leads = fields.Integer(string="عملاء جدد")
    kpi_quotations = fields.Integer(string="عروض أسعار")
    kpi_po_closed = fields.Integer(string="أوامر شراء")
    kpi_sales_value = fields.Float(string="قيمة المبيعات")
    issues = fields.Text(string="المعوقات")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.sales.report') or 'New'
        return super().create(vals_list)


class SimpleMrpSalesReportVisit(models.Model):
    _name = 'simple.mrp.sales.report.visit'
    _description = "زيارة مبيعات"
    _order = 'id'

    report_id = fields.Many2one(
        'simple.mrp.sales.report', string="التقرير", required=True, ondelete='cascade')
    visit_time = fields.Char(string="الوقت")
    client = fields.Char(string="العميل", required=True)
    contact = fields.Char(string="جهة الاتصال")
    visit_type = fields.Char(string="نوع الزيارة")
    outcome = fields.Char(string="المخرجات")
    follow_up = fields.Char(string="المتابعة")


class SimpleMrpSalesReportPipeline(models.Model):
    _name = 'simple.mrp.sales.report.pipeline'
    _description = "فرصة مبيعات"
    _order = 'id'

    report_id = fields.Many2one(
        'simple.mrp.sales.report', string="التقرير", required=True, ondelete='cascade')
    lead = fields.Char(string="الفرصة", required=True)
    value = fields.Float(string="القيمة المتوقعة")
    close_pct = fields.Float(string="احتمال الإغلاق %")
    next_step = fields.Char(string="الإجراء التالي")
