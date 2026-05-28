from datetime import date, timedelta

from odoo import models, fields, api


class PerformanceScore(models.Model):
    _name = 'rwasi.performance.score'
    _description = 'بطاقة أداء الورشة'
    _order = 'date_from desc, id desc'

    name = fields.Char(string='الفترة', compute='_compute_name', store=True)
    date_from = fields.Date(
        string='من', required=True,
        default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(
        string='إلى', required=True, default=lambda self: self._end_of_month())
    company_id = fields.Many2one(
        'res.company', string='الشركة', default=lambda self: self.env.company)

    # الأوزان (قابلة للتعديل، مجموعها يُفضّل 100)
    w_ontime = fields.Float(string='وزن التسليم بالموعد', default=30.0)
    w_satisfaction = fields.Float(string='وزن رضا العميل', default=30.0)
    w_attendance = fields.Float(string='وزن الحضور', default=15.0)
    w_productivity = fields.Float(string='وزن رفع الإنتاجية', default=25.0)

    # النتائج المحسوبة
    kpi_ontime = fields.Float(string='التسليم بالموعد %', readonly=True)
    kpi_satisfaction = fields.Float(string='رضا العميل %', readonly=True)
    kpi_attendance = fields.Float(string='مؤشر الحضور %', readonly=True)
    kpi_productivity = fields.Float(string='متوسط الإنتاجية (وحدة/ساعة)', readonly=True)
    kpi_productivity_growth = fields.Float(string='نمو الإنتاجية %', readonly=True)
    overall_score = fields.Float(string='الدرجة الإجمالية %', readonly=True)
    rating = fields.Selection([
        ('excellent', 'ممتاز'),
        ('very_good', 'جيد جداً'),
        ('good', 'جيد'),
        ('fair', 'مقبول'),
        ('weak', 'ضعيف'),
    ], string='التقييم', compute='_compute_rating', store=True)

    # تفاصيل
    closeouts_total = fields.Integer(string='عدد المشاريع المغلقة', readonly=True)
    total_work_hours = fields.Float(string='إجمالي ساعات العمل', readonly=True)
    total_output = fields.Float(string='إجمالي المنجز', readonly=True)

    @api.model
    def _end_of_month(self):
        first = date.today().replace(day=1)
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        return nxt - timedelta(days=1)

    @api.depends('date_from')
    def _compute_name(self):
        for rec in self:
            rec.name = ('بطاقة أداء %s' % rec.date_from.strftime('%Y-%m')) \
                if rec.date_from else 'بطاقة أداء'

    @api.depends('overall_score')
    def _compute_rating(self):
        for rec in self:
            s = rec.overall_score
            rec.rating = (
                'excellent' if s >= 90 else
                'very_good' if s >= 80 else
                'good' if s >= 70 else
                'fair' if s >= 60 else 'weak')

    def _avg(self, values):
        values = [v for v in values if v is not None]
        return (sum(values) / len(values)) if values else 0.0

    def action_compute(self):
        for rec in self:
            df, dt = rec.date_from, rec.date_to
            if not df or not dt:
                continue

            # 1) التسليم بالموعد + رضا العميل (من إغلاق المشاريع)
            closeouts = self.env['rwasi.project.closeout'].search([
                ('handover_date', '>=', df), ('handover_date', '<=', dt),
                ('company_id', '=', rec.company_id.id)])
            rec.closeouts_total = len(closeouts)
            rated = closeouts.filtered(
                lambda c: c.commitment_status in ('ontime', 'late'))
            ontime = len(rated.filtered(lambda c: c.commitment_status == 'ontime'))
            rec.kpi_ontime = (100.0 * ontime / len(rated)) if rated else 0.0
            sat = closeouts.filtered(lambda c: c.satisfaction)
            rec.kpi_satisfaction = (
                100.0 * sum(int(c.satisfaction) for c in sat) / (len(sat) * 5)) \
                if sat else 0.0

            # 2) الحضور (من التحضير اليومي: المتاح / (المتاح+الغائب))
            preps = self.env['rwasi.daily.preparation'].search([
                ('prep_date', '>=', df), ('prep_date', '<=', dt),
                ('company_id', '=', rec.company_id.id)])
            att = [100.0 * p.available_crew / (p.available_crew + p.absent_crew)
                   for p in preps if (p.available_crew + p.absent_crew) > 0]
            rec.kpi_attendance = rec._avg(att)

            # 3) الإنتاجية ونموّها (نفس الساعات → إنتاج أعلى)
            Worker = self.env['rwasi.daily.worker']
            cur = Worker.search([('date', '>=', df), ('date', '<=', dt),
                                 ('company_id', '=', rec.company_id.id)])
            rec.kpi_productivity = rec._avg([w.productivity for w in cur if w.productivity])
            rec.total_work_hours = sum(cur.mapped('actual_hours'))
            rec.total_output = sum(cur.mapped('output_qty'))
            span = (dt - df).days + 1
            prev = Worker.search([
                ('date', '>=', df - timedelta(days=span)),
                ('date', '<=', df - timedelta(days=1)),
                ('company_id', '=', rec.company_id.id)])
            prev_avg = rec._avg([w.productivity for w in prev if w.productivity])
            rec.kpi_productivity_growth = (
                100.0 * (rec.kpi_productivity - prev_avg) / prev_avg) if prev_avg else 0.0

            # درجات المكوّنات (0-100)
            s_ontime = rec.kpi_ontime
            s_sat = rec.kpi_satisfaction
            s_att = rec.kpi_attendance
            s_prod = max(0.0, min(100.0, 50.0 + rec.kpi_productivity_growth))
            wsum = (rec.w_ontime + rec.w_satisfaction + rec.w_attendance
                    + rec.w_productivity) or 1.0
            rec.overall_score = (
                rec.w_ontime * s_ontime + rec.w_satisfaction * s_sat
                + rec.w_attendance * s_att + rec.w_productivity * s_prod) / wsum
        return True
