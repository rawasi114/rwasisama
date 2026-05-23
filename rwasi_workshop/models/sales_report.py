from odoo import models, fields


# ============================================================
# RS-WS-22 — التقرير اليومي لموظف المبيعات (Sales Rep Daily Report)
# ============================================================
class SalesDailyReport(models.Model):
    _name = 'rwasi.sales.daily.report'
    _description = 'التقرير اليومي لموظف المبيعات (RS-WS-22)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.sales.daily.report'

    sales_rep = fields.Char(string='اسم الموظف')
    territory = fields.Char(string='المنطقة')
    report_date = fields.Date(
        string='التاريخ', default=fields.Date.context_today)
    reports_to = fields.Char(string='المشرف المباشر')

    visit_ids = fields.One2many(
        'rwasi.sales.visit.line', 'report_id', string='الزيارات اليومية')
    pipeline_ids = fields.One2many(
        'rwasi.sales.pipeline.line', 'report_id', string='الفرص المفتوحة وخطة الغد')

    # مؤشرات اليوم
    kpi_visits = fields.Integer(string='عدد الزيارات')
    kpi_new_leads = fields.Integer(string='عملاء جدد')
    kpi_quotations = fields.Integer(string='عروض أسعار')
    kpi_po_closed = fields.Integer(string='أوامر شراء')
    kpi_sales_value = fields.Float(string='قيمة المبيعات (SAR)')

    issues_support = fields.Text(string='المعوقات / الدعم المطلوب')

    # مشرف المبيعات / مدير المبيعات
    sales_supervisor_name = fields.Char(string='مشرف المبيعات - الاسم')
    sales_supervisor_date = fields.Date(string='مشرف المبيعات - التاريخ')
    sales_supervisor_signature = fields.Binary(string='مشرف المبيعات - التوقيع')
    sales_manager_name = fields.Char(string='مدير المبيعات - الاسم')
    sales_manager_date = fields.Date(string='مدير المبيعات - التاريخ')
    sales_manager_signature = fields.Binary(string='مدير المبيعات - التوقيع')


class SalesVisitLine(models.Model):
    _name = 'rwasi.sales.visit.line'
    _description = 'بند زيارة مبيعات'
    _order = 'sequence, id'

    report_id = fields.Many2one(
        'rwasi.sales.daily.report', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    visit_time = fields.Char(string='الوقت')
    client = fields.Char(string='اسم العميل / المنشأة', required=True)
    contact = fields.Char(string='جهة الاتصال')
    visit_type = fields.Char(string='نوع الزيارة')
    outcome = fields.Char(string='الموضوع / المخرجات')
    follow_up = fields.Char(string='المتابعة')


class SalesPipelineLine(models.Model):
    _name = 'rwasi.sales.pipeline.line'
    _description = 'بند فرصة مبيعات'
    _order = 'sequence, id'

    report_id = fields.Many2one(
        'rwasi.sales.daily.report', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    lead = fields.Char(string='العميل / الفرصة', required=True)
    value = fields.Float(string='القيمة المتوقعة')
    close_pct = fields.Float(string='احتمال الإغلاق %')
    next_step = fields.Char(string='الإجراء التالي')
