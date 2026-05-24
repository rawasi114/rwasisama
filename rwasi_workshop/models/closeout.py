from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

RATING = [
    ('5', 'ممتاز'),
    ('4', 'جيد جداً'),
    ('3', 'جيد'),
    ('2', 'مقبول'),
    ('1', 'ضعيف'),
]


# ============================================================
# RS-WS-20 — إغلاق وتسليم المشروع (Project Closeout & Handover)
# ============================================================
class ProjectCloseout(models.Model):
    _name = 'rwasi.project.closeout'
    _description = 'إغلاق وتسليم المشروع (RS-WS-20)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.project.closeout'

    work_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع', readonly=True, copy=False)
    contract_no = fields.Char(string='رقم العقد')
    handover_date = fields.Date(string='تاريخ التسليم')

    checklist_ids = fields.One2many(
        'rwasi.closeout.line', 'closeout_id', string='قائمة التحقق من الإغلاق')
    punch_ids = fields.One2many(
        'rwasi.punch.line', 'closeout_id', string='قائمة الملاحظات المتبقية')

    handover_statement = fields.Text(string='إقرار التسليم النهائي')

    # استبيان التقييم
    technician_rating = fields.Selection(RATING, string='تقييم الفنيين')
    finishing_quality = fields.Selection(RATING, string='جودة التشطيب')
    satisfaction = fields.Selection(RATING, string='رضا العميل')

    # الالتزام بالموعد (محسوب آلياً)
    date_started = fields.Date(
        related='work_order_id.start_date', string='تاريخ بدء التصنيع')
    promised_days = fields.Integer(string='المدة الموعودة (يوم)')
    installation_done_date = fields.Date(string='تاريخ إنهاء التركيب')
    delay_days = fields.Integer(
        string='أيام التأخير', compute='_compute_commitment', store=True)
    commitment_status = fields.Selection([
        ('na', 'غير محدد'),
        ('ontime', 'ملتزم بالموعد'),
        ('late', 'متأخر'),
    ], string='حالة الالتزام', compute='_compute_commitment', store=True)

    # المستلم وتوقيعه (توقيع واحد يغطّي الإقرار والاستبيان معاً)
    customer_sign_name = fields.Char(
        string='اسم المستلم',
        help='يُعبّأ تلقائياً باسم العميل من أمر البيع، ويُعدّل إن كان المستلم شخصاً آخر.')
    receiver_is_other = fields.Boolean(
        string='المستلم غير العميل صاحب الدفع')
    receiver_relation = fields.Char(string='صلة القرابة بالعميل')
    customer_signature = fields.Binary(string='توقيع المستلم')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('done', 'مغلق'),
        ('cancel', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True)

    @api.onchange('partner_id', 'receiver_is_other')
    def _onchange_receiver(self):
        for co in self:
            if not co.receiver_is_other:
                co.customer_sign_name = co.partner_id.name or False
                co.receiver_relation = False

    @api.model_create_multi
    def create(self, vals_list):
        # لا يُنشأ الإغلاق يدوياً: فقط كآخر خطوة في دورة أمر التصنيع
        if not self.env.context.get('from_work_order'):
            raise UserError(_(
                'لا يمكن إنشاء إغلاق مشروع يدوياً. يُنشأ تلقائياً كآخر خطوة في دورة '
                'أمر التصنيع عند الضغط على «إغلاق».'))
        return super().create(vals_list)

    @api.depends('date_started', 'promised_days', 'installation_done_date')
    def _compute_commitment(self):
        for co in self:
            if not (co.date_started and co.installation_done_date and co.promised_days):
                co.delay_days = 0
                co.commitment_status = 'na'
                continue
            deadline = co.date_started + timedelta(days=co.promised_days)
            delta = (co.installation_done_date - deadline).days
            co.delay_days = delta if delta > 0 else 0
            co.commitment_status = 'late' if delta > 0 else 'ontime'

    def action_done(self):
        for co in self:
            if not co.handover_statement:
                raise UserError(_('يجب كتابة إقرار التسليم النهائي قبل الإغلاق.'))
            if not (co.technician_rating and co.finishing_quality and co.satisfaction):
                raise UserError(_(
                    'يجب تعبئة استبيان التقييم (الفنيين / جودة التشطيب / رضا العميل) قبل الإغلاق.'))
            if not (co.customer_sign_name and co.customer_signature):
                raise UserError(_('يجب إدخال اسم المستلم وتوقيعه قبل الإغلاق.'))
            if co.receiver_is_other and not co.receiver_relation:
                raise UserError(_(
                    'حدّد صلة قرابة المستلم بالعميل (المستلم غير العميل صاحب الدفع).'))
            co.state = 'done'
            if not co.handover_date:
                co.handover_date = fields.Date.context_today(co)
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True


class CloseoutLine(models.Model):
    _name = 'rwasi.closeout.line'
    _description = 'بند تحقق من الإغلاق'
    _order = 'sequence, id'

    closeout_id = fields.Many2one(
        'rwasi.project.closeout', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    item = fields.Char(string='البند', required=True)
    result = fields.Selection([
        ('yes', 'يطابق'),
        ('no', 'لا يطابق'),
        ('na', 'غير منطبق'),
    ], string='النتيجة')
    reference = fields.Char(string='المرجع')


class PunchLine(models.Model):
    _name = 'rwasi.punch.line'
    _description = 'بند ملاحظة متبقية (Punch List)'
    _order = 'sequence, id'

    closeout_id = fields.Many2one(
        'rwasi.project.closeout', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    description = fields.Char(string='الوصف', required=True)
    owner = fields.Char(string='المسؤول')
    close_date = fields.Date(string='تاريخ الإغلاق')
