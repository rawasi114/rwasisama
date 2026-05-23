# -*- coding: utf-8 -*-
from odoo import models, fields, api

DEFAULT_STAGES = {
    'carpentry': ["تجهيز الخشب", "القص والتفصيل", "التجميع", "التشطيب والدهان", "التغليف"],
    'steel': ["تجهيز المعدن", "القص", "اللحام", "الجلفنة/الدهان", "الفحص النهائي"],
    'aluminum': ["تجهيز البروفايل", "القص والتجميع", "تركيب الزجاج", "تركيب الإكسسوار", "الفحص"],
    'cnc': ["إعداد الملف", "ضبط الماكينة", "القص/الحفر", "التنظيف", "الفحص"],
}


class SimpleMrpJobOrder(models.Model):
    _name = 'simple.mrp.job.order'
    _description = "أمر شغل"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="المرجع", required=True, copy=False, readonly=True,
                       default='New', tracking=True)
    workshop_type = fields.Selection([
        ('carpentry', "نجارة"),
        ('steel', "حدادة"),
        ('aluminum', "ألمنيوم"),
        ('cnc', "CNC"),
    ], string="نوع الورشة", default='carpentry', tracking=True)
    project = fields.Char(string="المشروع")
    order_id = fields.Many2one(
        'simple.mrp.order', string="أمر التصنيع", ondelete='set null', copy=False)
    wo_ref = fields.Char(string="مرجع أمر التشغيل")
    approved_dwg = fields.Char(string="المخطط المعتمد")
    due_date = fields.Date(string="تاريخ التسليم")
    element = fields.Char(string="العنصر")
    material = fields.Char(string="المادة")
    thickness = fields.Char(string="السماكة")
    dimensions = fields.Char(string="المقاسات")
    qty = fields.Float(string="الكمية", default=1.0)
    finish = fields.Char(string="التشطيب")
    spec_notes = fields.Text(string="مواصفات/ملاحظات")
    stage_ids = fields.One2many(
        'simple.mrp.job.order.stage', 'job_id', string="المراحل")

    state = fields.Selection([
        ('draft', "مسودة"),
        ('progress', "قيد التنفيذ"),
        ('done', "منجز"),
        ('cancel', "ملغي"),
    ], string="الحالة", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string="الشركة", default=lambda self: self.env.company)

    @api.onchange('workshop_type')
    def _onchange_workshop_type(self):
        for job in self:
            stages = DEFAULT_STAGES.get(job.workshop_type, [])
            job.stage_ids = [(5, 0, 0)] + [
                (0, 0, {'name': s, 'status': 'pending'}) for s in stages]

    def action_start(self):
        self.write({'state': 'progress'})
        return True

    def action_done(self):
        self.write({'state': 'done'})
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
                    'simple.mrp.job.order') or 'New'
        return super().create(vals_list)


class SimpleMrpJobOrderStage(models.Model):
    _name = 'simple.mrp.job.order.stage'
    _description = "مرحلة أمر شغل"
    _order = 'id'

    job_id = fields.Many2one(
        'simple.mrp.job.order', string="أمر الشغل", required=True, ondelete='cascade')
    name = fields.Char(string="المرحلة", required=True)
    responsible = fields.Char(string="المسؤول")
    date_from = fields.Date(string="من")
    date_to = fields.Date(string="إلى")
    status = fields.Selection([
        ('pending', "بالانتظار"),
        ('progress', "قيد التنفيذ"),
        ('done', "منجز"),
    ], string="الحالة", default='pending')
