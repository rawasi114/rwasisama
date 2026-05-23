from odoo import models, fields


# ============================================================
# RS-WS-11 — أمر شغل نجارة (Carpentry Job Order)
# ============================================================
class CarpentryJob(models.Model):
    _name = 'rwasi.carpentry.job'
    _description = 'أمر شغل نجارة (RS-WS-11)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.carpentry.job'

    work_order_id = fields.Many2one('rwasi.work.order', string='رقم أمر التشغيل')
    approved_dwg = fields.Char(string='المخطط المعتمد')
    due_date = fields.Date(string='تاريخ التسليم')

    # تفاصيل العنصر الخشبي
    element = fields.Char(string='وصف العنصر (باب / دولاب / كاونتر / كسوة)')
    wood_type = fields.Char(string='نوع الخشب (أرو / زان / Plywood / MDF)')
    thickness = fields.Char(string='السماكة')
    veneer_finish = fields.Char(string='القشرة / التشطيب')
    counter_top = fields.Char(string='الكاونترتوب')
    dimensions = fields.Char(string='المقاسات (L × W × H mm)')
    qty = fields.Float(string='الكمية')
    hardware = fields.Char(string='الإكسسوار / المفصلات')

    stage_ids = fields.One2many(
        'rwasi.carpentry.stage', 'job_id', string='مراحل التنفيذ')
    carpenter_notes = fields.Text(string='ملاحظات النجار / المشرف')


class CarpentryStage(models.Model):
    _name = 'rwasi.carpentry.stage'
    _description = 'مرحلة تنفيذ نجارة'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'rwasi.carpentry.job', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    stage = fields.Char(string='المرحلة', required=True)
    assigned_to = fields.Char(string='المسؤول')
    date_from = fields.Date(string='من')
    date_to = fields.Date(string='إلى')
    status = fields.Char(string='الحالة')


# ============================================================
# RS-WS-12 — أمر شغل حدادة (Steelwork Job Order)
# ============================================================
class SteelworkJob(models.Model):
    _name = 'rwasi.steelwork.job'
    _description = 'أمر شغل حدادة (RS-WS-12)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.steelwork.job'

    work_order_id = fields.Many2one('rwasi.work.order', string='رقم أمر التشغيل')
    approved_dwg = fields.Char(string='المخطط المعتمد')
    due_date = fields.Date(string='تاريخ التسليم')

    # مواصفات المنتج المعدني
    element = fields.Char(string='وصف العنصر (بوابة / درج / كانوبي / إطار)')
    material = fields.Char(string='نوع المعدن (C/S · S/S 304 · GI · Aluminum)')
    thickness = fields.Char(string='السماكة')
    section = fields.Char(string='المقطع (UC / UB / RHS / Pipe)')
    welding = fields.Char(string='طريقة اللحام (MIG / TIG / SMAW)')
    dimensions = fields.Char(string='المقاسات')
    qty = fields.Float(string='الكمية')
    finish = fields.Char(string='التشطيب السطحي (جلفنة / دهان حراري / بودرة)')

    # متطلبات الجودة
    qa_vt = fields.Boolean(string='فحص بصري للحام (VT)')
    qa_pt = fields.Boolean(string='اختبار سوائل نافذة (PT)')
    qa_ut = fields.Boolean(string='موجات فوق صوتية (UT)')
    qa_rt = fields.Boolean(string='أشعة (RT)')
    qa_wqt = fields.Boolean(string='شهادة لحام معتمد WQT/WPS')
    qa_dft = fields.Boolean(string='اختبار الطلاء DFT')

    stage_ids = fields.One2many(
        'rwasi.steelwork.stage', 'job_id', string='مراحل التنفيذ')


class SteelworkStage(models.Model):
    _name = 'rwasi.steelwork.stage'
    _description = 'مرحلة تنفيذ حدادة'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'rwasi.steelwork.job', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    stage = fields.Char(string='المرحلة', required=True)
    assigned_to = fields.Char(string='المسؤول')
    date_from = fields.Date(string='من')
    date_to = fields.Date(string='إلى')
    status = fields.Char(string='الحالة')


# ============================================================
# RS-WS-13 — أمر شغل ألمنيوم (Aluminum Job Order)
# ============================================================
class AluminumJob(models.Model):
    _name = 'rwasi.aluminum.job'
    _description = 'أمر شغل ألمنيوم (RS-WS-13)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.aluminum.job'

    work_order_id = fields.Many2one('rwasi.work.order', string='رقم أمر التشغيل')
    approved_dwg = fields.Char(string='المخطط المعتمد')
    due_date = fields.Date(string='تاريخ التسليم')

    # مواصفات المنتج
    element = fields.Char(string='نوع العنصر (نافذة / كيرتن وول / واجهة / كلادينج)')
    profile_system = fields.Char(string='نظام البروفايل (Reynaers / Schüco / Local)')
    profile_thickness = fields.Char(string='سمك البروفايل')
    glazing = fields.Char(string='نوع الزجاج (Double / Laminated / Low-E)')
    glass_thickness = fields.Char(string='سمك الزجاج')
    dimensions = fields.Char(string='المقاسات (W × H mm)')
    qty = fields.Float(string='الكمية')
    finish_color = fields.Char(string='لون التشطيب (RAL — / Anodized)')

    accessory_ids = fields.One2many(
        'rwasi.aluminum.accessory', 'job_id', string='الإكسسوار والملحقات')

    # اختبارات الأداء المطلوبة
    test_water = fields.Boolean(string='اختبار تسرب المياه')
    test_air = fields.Boolean(string='اختبار تسرب الهواء')
    test_wind_load = fields.Boolean(string='مقاومة الأحمال')
    test_u_value = fields.Boolean(string='اختبار العزل الحراري (U-Value)')
    test_mockup = fields.Boolean(string='عينة معتمدة (Mock-up)')


class AluminumAccessory(models.Model):
    _name = 'rwasi.aluminum.accessory'
    _description = 'إكسسوار ألمنيوم'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'rwasi.aluminum.job', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    item = fields.Char(string='وصف الإكسسوار', required=True)
    model = fields.Char(string='الموديل')
    origin = fields.Char(string='المنشأ')
    qty = fields.Float(string='الكمية')


# ============================================================
# RS-WS-14 — أمر شغل CNC (CNC Job Order)
# ============================================================
class CncJob(models.Model):
    _name = 'rwasi.cnc.job'
    _description = 'أمر شغل CNC (RS-WS-14)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.cnc.job'

    work_order_id = fields.Many2one('rwasi.work.order', string='رقم أمر التشغيل')
    cad_file = fields.Char(string='ملف القص (DXF / CAD)')
    due_date = fields.Date(string='تاريخ التسليم')

    # إعدادات التشغيل
    machine = fields.Char(string='نوع الماكينة (Router / Plasma / Laser / Mill)')
    machine_no = fields.Char(string='رقم الماكينة')
    operator = fields.Char(string='المُشغّل')
    material = fields.Char(string='نوع الخامة')
    thickness = fields.Char(string='السماكة')
    pcs = fields.Integer(string='عدد القطع')
    tool_bit = fields.Char(string='الأداة / الريشة')
    rpm = fields.Float(string='دوران المغزل (RPM)')
    feed_rate = fields.Float(string='سرعة التغذية (mm/min)')
    sheet_size = fields.Char(string='أبعاد اللوح الخام')
    yield_pct = fields.Float(string='نسبة الاستفادة المتوقعة %')

    run_ids = fields.One2many(
        'rwasi.cnc.run', 'job_id', string='سجل التشغيل')


class CncRun(models.Model):
    _name = 'rwasi.cnc.run'
    _description = 'بند سجل تشغيل CNC'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'rwasi.cnc.job', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    part = fields.Char(string='الجزء', required=True)
    qty = fields.Float(string='العدد')
    start = fields.Char(string='بدء التشغيل')
    end = fields.Char(string='انتهاء')
    cycle = fields.Char(string='زمن الدورة')
    accept_reject = fields.Selection([
        ('accept', 'قبول'),
        ('reject', 'رفض'),
    ], string='قبول/رفض')
