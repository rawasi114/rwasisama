import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .base import WORKSHOP_SCOPE


class WorkOrder(models.Model):
    """RS-WS-01 — أمر تصنيع: رأس واحد لكل أمر بيع، يحوي أوامر عمل متعددة."""
    _name = 'rwasi.work.order'
    _description = 'أمر تصنيع (RS-WS-01)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.work.order'

    # واحد لواحد مع أمر البيع
    sale_order_id = fields.Many2one(
        'sale.order', string='أمر البيع', readonly=True, copy=False, index=True)

    # بيانات الأمر
    priority = fields.Selection([
        ('normal', 'عادي'),
        ('urgent', 'عاجل'),
    ], string='الأولوية', default='normal', tracking=True)
    scope_of_work = fields.Text(string='وصف العمل العام')
    start_date = fields.Date(string='تاريخ بدء التنفيذ')
    required_date = fields.Date(string='تاريخ التسليم المطلوب')
    est_duration = fields.Integer(string='المدة التقديرية (يوم)')
    drawing_ref = fields.Char(string='المرجع / المخططات')
    workshop_scope_summary = fields.Char(
        string='الأقسام', compute='_compute_scope_summary')

    # أوامر العمل (واحد لكل منتج)
    job_ids = fields.One2many(
        'rwasi.work.job', 'work_order_id', string='أوامر العمل')
    job_count = fields.Integer(compute='_compute_counts')

    # طلبات المواد (متعددة، قابلة للتكرار لنفس أمر العمل)
    material_request_ids = fields.One2many(
        'rwasi.material.request', 'work_order_id', string='طلبات المواد')
    material_request_count = fields.Integer(compute='_compute_counts')

    # طلبات الشراء (عبر طلبات المواد)
    purchase_order_ids = fields.One2many(
        'purchase.order', 'workshop_order_id', string='طلبات الشراء')
    purchase_order_count = fields.Integer(compute='_compute_counts')

    # المتطلبات والاشتراطات
    req_approved_dwgs = fields.Boolean(string='مخططات معتمدة')
    req_sample_approved = fields.Boolean(string='عينة موافق عليها')
    req_material_approval = fields.Boolean(string='اعتماد المواد')
    req_third_party_test = fields.Boolean(string='طرف ثالث / فحص')
    req_site_install = fields.Boolean(string='تركيب بالموقع')
    req_special_packing = fields.Boolean(string='تغليف خاص')

    # الإغلاق
    closeout_id = fields.Many2one(
        'rwasi.project.closeout', string='إغلاق المشروع', readonly=True, copy=False)
    closeout_count = fields.Integer(compute='_compute_counts')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('in_production', 'قيد التصنيع'),
        ('finished', 'انتهى التصنيع'),
        ('delivered', 'تم التسليم'),
        ('done', 'مغلق'),
        ('cancel', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True,
        group_expand='_group_expand_state')

    # حالة السداد
    payment_status = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئي'),
        ('paid', 'مدفوع بالكامل'),
    ], string='حالة السداد', compute='_compute_payment_status')
    paid_ratio = fields.Float(
        string='نسبة السداد', compute='_compute_payment_status')

    # تسليم العميل
    customer_sign_name = fields.Char(string='اسم مستلم العميل')
    customer_sign_date = fields.Date(string='تاريخ التسليم للعميل')
    customer_signature = fields.Binary(string='توقيع العميل')

    @api.model
    def _group_expand_state(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

    @api.depends('job_ids.workshop_scope')
    def _compute_scope_summary(self):
        scope_label = dict(WORKSHOP_SCOPE)
        for wo in self:
            scopes = sorted({j.workshop_scope for j in wo.job_ids if j.workshop_scope})
            wo.workshop_scope_summary = ' / '.join(
                scope_label.get(s, s) for s in scopes)

    @api.depends('sale_order_id', 'sale_order_id.amount_total',
                 'sale_order_id.workshop_payment_ids.amount')
    def _compute_payment_status(self):
        for wo in self:
            so = wo.sale_order_id.sudo() if wo.sale_order_id else False
            order_total = so.amount_total if so else 0.0
            collected = sum(so.workshop_payment_ids.mapped('amount')) if so else 0.0
            ratio = (collected / order_total) if order_total else 0.0
            wo.paid_ratio = ratio
            if order_total <= 0:
                wo.payment_status = 'not_paid'
            elif ratio >= 0.999:
                wo.payment_status = 'paid'
            elif ratio > 0.0:
                wo.payment_status = 'partial'
            else:
                wo.payment_status = 'not_paid'

    @api.depends('job_ids', 'material_request_ids', 'purchase_order_ids', 'closeout_id')
    def _compute_counts(self):
        for wo in self:
            wo.job_count = len(wo.job_ids)
            wo.material_request_count = len(wo.material_request_ids)
            wo.purchase_order_count = len(wo.purchase_order_ids)
            wo.closeout_count = 1 if wo.closeout_id else 0

    @api.model
    def _make_name_from_so(self, so_name):
        """يولّد رقم أمر التصنيع من رقم أمر البيع باختلاف حرف البادئة (S → M)."""
        if not so_name:
            return self.env['ir.sequence'].next_by_code(self._sequence_code) or 'New'
        if re.match(r'^[A-Za-z]+', so_name):
            return re.sub(r'^[A-Za-z]+', 'M', so_name)
        return 'M' + so_name

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('from_sale_order'):
            raise UserError(_(
                'لا يمكن إنشاء أمر تصنيع يدوياً. '
                'يُنشأ تلقائياً فقط عند تأكيد عرض السعر للمنتجات الورشية.'))
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New') and vals.get('sale_order_id'):
                so = self.env['sale.order'].browse(vals['sale_order_id'])
                vals['name'] = self._make_name_from_so(so.name)
        return super().create(vals_list)

    def write(self, vals):
        # أمر التصنيع المغلق نهائي
        if 'state' in vals and vals['state'] != 'done':
            locked = self.filtered(lambda w: w.state == 'done')
            if locked:
                raise UserError(_(
                    'لا يمكن تغيير حالة أمر تصنيع مغلق. '
                    'أنشئ أمراً جديداً إن لزم الأمر.'))
        return super().write(vals)

    # ---------------- أزرار سير العمل ----------------
    def action_confirm(self):
        for wo in self:
            if wo.state != 'draft':
                continue
            if not wo.job_ids:
                raise UserError(_('لا يمكن تأكيد أمر تصنيع بلا أوامر عمل.'))
            wo.state = 'confirmed'
        return True

    def action_start_production(self):
        for wo in self:
            if wo.state != 'confirmed':
                raise UserError(_('يجب تأكيد الأمر أولاً قبل بدء التصنيع.'))
            if wo.paid_ratio < 0.5:
                raise UserError(_(
                    'لا يمكن بدء التصنيع قبل سداد دفعة أولى لا تقل عن 50%.'))
            wo.state = 'in_production'
            if not wo.start_date:
                wo.start_date = fields.Date.context_today(wo)
        return True

    def action_finish_production(self):
        for wo in self:
            if wo.state != 'in_production':
                raise UserError(_('لا يمكن إنهاء التصنيع إلا أثناء التصنيع.'))
            wo.state = 'finished'
        return True

    def action_deliver(self):
        for wo in self:
            if wo.state != 'finished':
                raise UserError(_('لا يمكن التسليم إلا بعد إنهاء التصنيع.'))
            if wo.payment_status != 'paid':
                raise UserError(_(
                    'لا يمكن التسليم قبل سداد كامل قيمة العمل.'))
            wo.state = 'delivered'
            if not wo.customer_sign_date:
                wo.customer_sign_date = fields.Date.context_today(wo)
        return True

    def action_close(self):
        self.ensure_one()
        if self.state != 'delivered':
            raise UserError(_('لا يمكن إغلاق الأمر إلا بعد التسليم للعميل.'))
        self.state = 'done'
        self._create_closeout()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إغلاق وتسليم المشروع'),
            'res_model': 'rwasi.project.closeout',
            'view_mode': 'form',
            'res_id': self.closeout_id.id,
        }

    def _create_closeout(self):
        self.ensure_one()
        if self.closeout_id:
            return
        co = self.env['rwasi.project.closeout'].sudo().with_context(
            from_work_order=True).create({
                'work_order_id': self.id,
                'partner_id': self.partner_id.id,
                'project_ref': self.project_ref,
                'customer_sign_name': self.customer_sign_name or self.partner_id.name,
                'handover_date': fields.Date.context_today(self),
            })
        self.closeout_id = co.id
        self.message_post(body=_('أُنشئ نموذج إغلاق المشروع %s.') % co.name)

    def action_cancel(self):
        for wo in self:
            if wo.state in ('delivered', 'done'):
                raise UserError(_('لا يمكن إلغاء أمر بعد التسليم أو الإغلاق.'))
            wo.state = 'cancel'

    def action_draft(self):
        for wo in self:
            if wo.state in ('delivered', 'done'):
                raise UserError(_('لا يمكن إعادة أمر مُسلَّم أو مغلق إلى مسودة.'))
            wo.state = 'draft'

    # ---------------- أزرار ذكية ----------------
    def _stat_action(self, name, model, domain):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_work_order_id': self.id},
        }

    def action_view_jobs(self):
        return self._stat_action(
            _('أوامر العمل'), 'rwasi.work.job',
            [('work_order_id', '=', self.id)])

    def action_view_material_requests(self):
        return self._stat_action(
            _('طلبات المواد'), 'rwasi.material.request',
            [('work_order_id', '=', self.id)])

    def action_view_purchase_orders(self):
        return self._stat_action(
            _('طلبات الشراء'), 'purchase.order',
            [('workshop_order_id', '=', self.id)])

    def action_view_closeout(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إغلاق المشروع'),
            'res_model': 'rwasi.project.closeout',
            'view_mode': 'form,list',
            'res_id': self.closeout_id.id,
        }


class WorkOrderJob(models.Model):
    """أمر عمل ضمن أمر التصنيع — واحد لكل منتج من أمر البيع."""
    _name = 'rwasi.work.job'
    _description = 'أمر عمل'
    _order = 'work_order_id, sequence, id'

    work_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع', required=True,
        ondelete='cascade', index=True)
    sale_line_id = fields.Many2one(
        'sale.order.line', string='بند أمر البيع', readonly=True, copy=False)
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='رقم أمر العمل', default='New', readonly=True, copy=False)
    company_id = fields.Many2one(
        related='work_order_id.company_id', store=True)
    partner_id = fields.Many2one(
        related='work_order_id.partner_id', store=True)

    product_id = fields.Many2one(
        'product.product', string='المنتج المُصنَّع', required=True)
    product_qty = fields.Float(string='الكمية', default=1.0)
    workshop_scope = fields.Selection(
        WORKSHOP_SCOPE, string='قسم التنفيذ', tracking=True)
    description = fields.Text(string='وصف العمل')
    est_duration = fields.Integer(string='المدة التقديرية (يوم)')
    start_date = fields.Date()
    end_date = fields.Date()

    line_ids = fields.One2many(
        'rwasi.work.order.line', 'job_id', string='بنود التنفيذ')
    material_request_ids = fields.One2many(
        'rwasi.material.request', 'work_job_id', string='طلبات المواد')
    material_request_count = fields.Integer(compute='_compute_counts')

    status = fields.Selection([
        ('draft', 'مسودة'),
        ('in_production', 'قيد التصنيع'),
        ('finished', 'منجز'),
        ('cancel', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True)

    @api.depends('material_request_ids')
    def _compute_counts(self):
        for j in self:
            j.material_request_count = len(j.material_request_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New') and vals.get('work_order_id'):
                wo = self.env['rwasi.work.order'].browse(vals['work_order_id'])
                next_no = len(wo.job_ids) + 1
                vals['name'] = '%s-J%02d' % (wo.name or 'WO', next_no)
        return super().create(vals_list)

    def action_start(self):
        self.write({'status': 'in_production'})

    def action_finish(self):
        self.write({'status': 'finished'})

    def action_view_material_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات المواد لهذا الأمر'),
            'res_model': 'rwasi.material.request',
            'view_mode': 'list,form',
            'domain': [('work_job_id', '=', self.id)],
            'context': {
                'default_work_order_id': self.work_order_id.id,
                'default_work_job_id': self.id,
            },
        }


class WorkOrderLine(models.Model):
    """بند تنفيذ ضمن أمر العمل."""
    _name = 'rwasi.work.order.line'
    _description = 'بند تنفيذ'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'rwasi.work.job', string='أمر العمل', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    description = fields.Char(string='وصف البند', required=True)
    qty = fields.Float(string='الكمية', default=1.0)
    uom = fields.Char(string='الوحدة')
    item_ref = fields.Char(string='مرجع البند')
    status = fields.Char(string='الحالة')
