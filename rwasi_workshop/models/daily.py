from odoo import models, fields


# ============================================================
# RS-WS-05 — التحضير اليومي للورشة (Daily Preparation Sheet)
# ============================================================
class DailyPreparation(models.Model):
    _name = 'rwasi.daily.preparation'
    _description = 'التحضير اليومي للورشة (RS-WS-05)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.daily.preparation'

    prep_day = fields.Char(string='اليوم')
    prep_date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    workshop = fields.Char(string='الورشة / القسم')
    shift_supervisor = fields.Char(string='مشرف الوردية')

    line_ids = fields.One2many(
        'rwasi.daily.preparation.line', 'preparation_id', string='الأعمال المخططة لليوم')

    # الجاهزية اليومية
    available_crew = fields.Integer(string='عدد العمالة المتاحة')
    absent_crew = fields.Integer(string='عدد العمالة الغائبة')
    ready_equipment = fields.Integer(string='معدات جاهزة')
    under_maint_equipment = fields.Integer(string='معدات تحت الصيانة')
    chk_materials_ready = fields.Boolean(string='مواد متوفرة')
    chk_drawings_approved = fields.Boolean(string='مخططات معتمدة')
    chk_toolbox_talk = fields.Boolean(string='تنبيه أمن وسلامة')
    chk_ppe_verified = fields.Boolean(string='أدوات الحماية الشخصية')
    chk_targets_reviewed = fields.Boolean(string='التحقق من الأهداف اليومية')

    expected_bottlenecks = fields.Text(string='المعوقات المتوقعة')


class DailyPreparationLine(models.Model):
    _name = 'rwasi.daily.preparation.line'
    _description = 'بند عمل مخطط لليوم'
    _order = 'sequence, id'

    preparation_id = fields.Many2one(
        'rwasi.daily.preparation', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    wo_no = fields.Char(string='رقم أمر التشغيل')
    task = fields.Char(string='وصف العمل', required=True)
    assigned_to = fields.Char(string='المسؤول')
    hours = fields.Float(string='الساعات')
    expected_output = fields.Char(string='المخرج المتوقع')


# ============================================================
# RS-WS-06 — التقرير اليومي للورشة (Daily Workshop Report)
# ============================================================
class DailyReport(models.Model):
    _name = 'rwasi.daily.report'
    _description = 'التقرير اليومي للورشة (RS-WS-06)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.daily.report'

    report_date = fields.Date(
        string='التاريخ', default=fields.Date.context_today)
    workshop = fields.Char(string='الورشة')
    weather = fields.Char(string='حالة الطقس')
    working_hours = fields.Char(string='ساعات العمل')

    line_ids = fields.One2many(
        'rwasi.daily.report.line', 'report_id', string='الإنجازات اليومية')

    # الموارد المستخدمة
    crew_count = fields.Integer(string='العمالة (عدد)')
    man_hours = fields.Float(string='إجمالي ساعات العمل')
    equipment_used = fields.Char(string='المعدات المستخدمة')
    equipment_hours = fields.Float(string='ساعات تشغيل المعدات')

    issues_delays = fields.Text(string='المعوقات والتأخيرات')
    plan_tomorrow = fields.Text(string='خطة الغد')


class DailyReportLine(models.Model):
    _name = 'rwasi.daily.report.line'
    _description = 'بند إنجاز يومي'
    _order = 'sequence, id'

    report_id = fields.Many2one(
        'rwasi.daily.report', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    wo_no = fields.Char(string='رقم أمر التشغيل')
    description = fields.Char(string='الوصف', required=True)
    planned = fields.Float(string='المخطط')
    done = fields.Float(string='المُنجز')
    completion = fields.Float(string='% الإنجاز')
    remaining = fields.Float(string='المتبقي')
