# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

RATING = [
    ('5', "ممتاز"),
    ('4', "جيد جداً"),
    ('3', "جيد"),
    ('2', "مقبول"),
    ('1', "ضعيف"),
]


class SimpleMrpCloseout(models.Model):
    _name = 'simple.mrp.closeout'
    _description = "إغلاق وتسليم المشروع"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    project = fields.Char(string="المشروع", required=True)
    client = fields.Char(string="العميل")
    contract_no = fields.Char(string="رقم العقد")
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    handover_date = fields.Date(string="تاريخ التسليم")
    checklist_ids = fields.One2many(
        'simple.mrp.closeout.check', 'closeout_id', string="قائمة التحقق")
    punch_ids = fields.One2many(
        'simple.mrp.closeout.punch', 'closeout_id', string="الملاحظات المتبقية")
    handover_statement = fields.Text(string="إقرار التسليم")

    technician_rating = fields.Selection(RATING, string="تقييم الفنيين")
    satisfaction = fields.Selection(RATING, string="رضا العميل")
    finishing_quality = fields.Selection(RATING, string="جودة التشطيب")

    date_started = fields.Datetime(
        related='order_id.date_started', string="تاريخ بدء التصنيع")
    promised_days = fields.Integer(string="المدة الموعودة (يوم)")
    installation_done_date = fields.Date(string="تاريخ إنهاء التركيب")
    delay_days = fields.Integer(string="أيام التأخير", compute='_compute_commitment',
                                store=True)
    commitment_status = fields.Selection([
        ('na', "غير محدد"),
        ('ontime', "ملتزم بالموعد"),
        ('late', "متأخر"),
    ], string="حالة الالتزام", compute='_compute_commitment', store=True)

    customer_signature = fields.Binary(string="توقيع العميل")
    customer_sign_name = fields.Char(string="اسم المستلم")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('done', "منجز"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.depends('date_started', 'promised_days', 'installation_done_date')
    def _compute_commitment(self):
        from datetime import timedelta
        for co in self:
            if not co.date_started or not co.installation_done_date or not co.promised_days:
                co.delay_days = 0
                co.commitment_status = 'na'
                continue
            deadline = fields.Date.to_date(co.date_started) + timedelta(days=co.promised_days)
            delta = (co.installation_done_date - deadline).days
            co.delay_days = delta if delta > 0 else 0
            co.commitment_status = 'late' if delta > 0 else 'ontime'

    def action_done(self):
        for co in self:
            if not (co.technician_rating and co.satisfaction and co.finishing_quality):
                raise UserError(
                    _("يجب تعبئة تقييمات الفنيين وجودة التشطيب ورضا العميل قبل الإغلاق."))
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'simple.mrp.closeout') or 'New'
        return super().create(vals_list)


class SimpleMrpCloseoutCheck(models.Model):
    _name = 'simple.mrp.closeout.check'
    _description = "بند تحقق إغلاق"
    _order = 'id'

    closeout_id = fields.Many2one(
        'simple.mrp.closeout', string="الإغلاق", required=True, ondelete='cascade')
    name = fields.Char(string="البند", required=True)
    result = fields.Selection([
        ('yes', "نعم"),
        ('no', "لا"),
        ('na', "غير منطبق"),
    ], string="النتيجة")
    reference = fields.Char(string="المرجع")


class SimpleMrpCloseoutPunch(models.Model):
    _name = 'simple.mrp.closeout.punch'
    _description = "ملاحظة متبقية"
    _order = 'id'

    closeout_id = fields.Many2one(
        'simple.mrp.closeout', string="الإغلاق", required=True, ondelete='cascade')
    name = fields.Char(string="الوصف", required=True)
    owner = fields.Char(string="المسؤول")
    close_date = fields.Date(string="تاريخ الإغلاق")
