from odoo import models, fields


# ============================================================
# RS-WS-17 — سجل صيانة المعدات والآلات (Machine Maintenance Log)
# ============================================================
class MaintenanceLog(models.Model):
    _name = 'rwasi.maintenance.log'
    _description = 'سجل صيانة المعدات والآلات (RS-WS-17)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.maintenance.log'

    machine = fields.Char(string='اسم المعدة')
    asset_no = fields.Char(string='رقم الأصل')
    location = fields.Char(string='الموقع / الورشة')
    year = fields.Char(string='سنة الإنتاج')

    line_ids = fields.One2many(
        'rwasi.maintenance.line', 'log_id', string='سجل أعمال الصيانة')

    # جدول الصيانة الوقائية
    pm_daily = fields.Boolean(string='يومي')
    pm_weekly = fields.Boolean(string='أسبوعي')
    pm_monthly = fields.Boolean(string='شهري')
    pm_quarterly = fields.Boolean(string='ربع سنوي')
    pm_annual = fields.Boolean(string='سنوي')

    # فني الصيانة / مشرف الصيانة
    technician_name = fields.Char(string='فني الصيانة - الاسم')
    technician_date = fields.Date(string='فني الصيانة - التاريخ')
    technician_signature = fields.Binary(string='فني الصيانة - التوقيع')


class MaintenanceLine(models.Model):
    _name = 'rwasi.maintenance.line'
    _description = 'بند صيانة'
    _order = 'sequence, id'

    log_id = fields.Many2one(
        'rwasi.maintenance.log', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    date = fields.Date(string='التاريخ')
    maint_type = fields.Selection([
        ('preventive', 'وقائية'),
        ('corrective', 'علاجية'),
    ], string='النوع')
    work_fault = fields.Char(string='وصف العمل / العطل', required=True)
    spares = fields.Char(string='قطع الغيار')
    downtime = fields.Float(string='ساعات التوقف')
    technician = fields.Char(string='الفني')
