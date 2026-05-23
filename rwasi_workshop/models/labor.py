from odoo import models, fields


# ============================================================
# RS-WS-07 — كشف حضور وانصراف العمالة (Attendance Sheet)
# ============================================================
class AttendanceSheet(models.Model):
    _name = 'rwasi.attendance.sheet'
    _description = 'كشف حضور وانصراف العمالة (RS-WS-07)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.attendance.sheet'

    att_date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    workshop = fields.Char(string='الورشة')
    shift = fields.Selection([
        ('day', 'نهارية'),
        ('night', 'ليلية'),
    ], string='رقم الوردية')
    total_present = fields.Integer(string='إجمالي الحضور')

    line_ids = fields.One2many(
        'rwasi.attendance.line', 'sheet_id', string='كشف الحضور')


class AttendanceLine(models.Model):
    _name = 'rwasi.attendance.line'
    _description = 'بند حضور عامل'
    _order = 'sequence, id'

    sheet_id = fields.Many2one(
        'rwasi.attendance.sheet', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    worker_id_no = fields.Char(string='رقم البصمة')
    worker_name = fields.Char(string='اسم العامل', required=True)
    trade = fields.Char(string='المهنة')
    time_in = fields.Char(string='دخول')
    time_out = fields.Char(string='خروج')
    overtime = fields.Float(string='إضافي')
    total = fields.Float(string='إجمالي')


# ============================================================
# RS-WS-08 — بطاقة وقت العامل (Job Time Card)
# ============================================================
class TimeCard(models.Model):
    _name = 'rwasi.time.card'
    _description = 'بطاقة وقت العامل (RS-WS-08)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.time.card'

    worker_name = fields.Char(string='اسم العامل')
    worker_id_no = fields.Char(string='رقم البصمة')
    trade = fields.Char(string='المهنة')
    week_ending = fields.Date(string='الأسبوع المنتهي')

    line_ids = fields.One2many(
        'rwasi.time.card.line', 'card_id', string='توزيع الساعات على المهام')

    # ملخص الأسبوع
    regular_hrs = fields.Float(string='الساعات العادية')
    overtime_hrs = fields.Float(string='الساعات الإضافية')
    leave_hrs = fields.Float(string='الإجازات')
    week_total = fields.Float(string='إجمالي الأسبوع')


class TimeCardLine(models.Model):
    _name = 'rwasi.time.card.line'
    _description = 'بند توزيع ساعات العامل'
    _order = 'sequence, id'

    card_id = fields.Many2one(
        'rwasi.time.card', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    wo = fields.Char(string='أمر التشغيل')
    task = fields.Char(string='وصف المهمة', required=True)
    sat = fields.Float(string='السبت')
    sun = fields.Float(string='الأحد')
    mon = fields.Float(string='الإثنين')
    tue = fields.Float(string='الثلاثاء')
    wed = fields.Float(string='الأربعاء')
    thu = fields.Float(string='الخميس')
    total = fields.Float(string='الإجمالي')


# ============================================================
# RS-WS-09 — إنتاجية العمالة (Labor Productivity)
# ============================================================
class LaborProductivity(models.Model):
    _name = 'rwasi.labor.productivity'
    _description = 'إنتاجية العمالة (RS-WS-09)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.labor.productivity'

    period_from = fields.Date(string='الفترة من')
    period_to = fields.Date(string='الفترة إلى')
    workshop = fields.Char(string='الورشة / القسم')
    crew_size = fields.Integer(string='إجمالي العمالة')

    line_ids = fields.One2many(
        'rwasi.labor.productivity.line', 'productivity_id', string='قياس الإنتاجية حسب البند')

    # مؤشرات الأداء
    total_mh = fields.Float(string='إجمالي ساعات العمل')
    total_output = fields.Float(string='إجمالي الإنتاج')
    productivity_factor = fields.Float(string='معدل الإنتاجية')
    variance = fields.Float(string='الانحراف عن المعياري %')

    variance_analysis = fields.Text(string='تحليل الانحرافات وخطة التحسين')


class LaborProductivityLine(models.Model):
    _name = 'rwasi.labor.productivity.line'
    _description = 'بند إنتاجية'
    _order = 'sequence, id'

    productivity_id = fields.Many2one(
        'rwasi.labor.productivity', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    item = fields.Char(string='رقم البند')
    description = fields.Char(string='الوصف', required=True)
    uom = fields.Char(string='الوحدة')
    output = fields.Float(string='المُنجز')
    man_hrs = fields.Float(string='ساعات العمل')
    std_rate = fields.Float(string='المعدل المعياري')
    actual_rate = fields.Float(string='المعدل الفعلي')
