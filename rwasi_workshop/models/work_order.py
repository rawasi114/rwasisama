import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .base import WORKSHOP_SCOPE


class WorkOrder(models.Model):
    """RS-WS-01 — أمر تشغيل / أمر تصنيع (النموذج المركزي لدورة حياة العمل)."""
    _name = 'rwasi.work.order'
    _description = 'أمر تشغيل / تصنيع (RS-WS-01)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.work.order'

    # الربط بأمر البيع
    sale_order_id = fields.Many2one(
        'sale.order', string='أمر البيع', readonly=True, copy=False, index=True)
    sale_line_id = fields.Many2one(
        'sale.order.line', string='بند أمر البيع', readonly=True, copy=False)
    product_id = fields.Many2one(
        'product.product', string='المنتج المراد تصنيعه')
    product_qty = fields.Float(string='الكمية', default=1.0)

    # بيانات الأمر
    workshop_scope = fields.Selection(
        WORKSHOP_SCOPE, string='قسم التنفيذ', tracking=True)
    priority = fields.Selection([
        ('normal', 'عادي'),
        ('urgent', 'عاجل'),
    ], string='الأولوية', default='normal', tracking=True)
    scope_of_work = fields.Text(string='وصف العمل المطلوب')
    start_date = fields.Date(string='تاريخ بدء التنفيذ')
    required_date = fields.Date(string='تاريخ التسليم المطلوب')
    est_duration = fields.Integer(string='المدة التقديرية (يوم)')
    drawing_ref = fields.Char(string='المرجع / المخططات')

    # بنود التنفيذ
    line_ids = fields.One2many(
        'rwasi.work.order.line', 'order_id', string='بنود التنفيذ')

    # المتطلبات والاشتراطات
    req_approved_dwgs = fields.Boolean(string='مخططات معتمدة')
    req_sample_approved = fields.Boolean(string='عينة موافق عليها')
    req_material_approval = fields.Boolean(string='اعتماد المواد')
    req_third_party_test = fields.Boolean(string='طرف ثالث / فحص')
    req_site_install = fields.Boolean(string='تركيب بالموقع')
    req_special_packing = fields.Boolean(string='تغليف خاص')

    # ضبط العمليات
    materials_available = fields.Boolean(
        string='المواد متوفرة بالمخزون',
        help='عند تفعيله لا يمكن طلب مواد جديدة لأنها متوفرة، ويتم الانتقال مباشرة لاستلام المواد.')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('material_requested', 'تم طلب المواد'),
        ('material_received', 'تم استلام المواد'),
        ('in_production', 'قيد التصنيع'),
        ('finished', 'انتهى التصنيع'),
        ('delivered', 'تم التسليم'),
        ('done', 'مغلق'),
        ('cancel', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True, group_expand='_group_expand_state')

    # المستندات المرتبطة
    requisition_ids = fields.One2many(
        'rwasi.material.requisition', 'work_order_id', string='طلبات المواد')
    receipt_ids = fields.One2many(
        'rwasi.material.receipt', 'work_order_id', string='استلام المواد')
    requisition_count = fields.Integer(compute='_compute_doc_counts')
    receipt_count = fields.Integer(compute='_compute_doc_counts')

    # تسليم العميل
    customer_sign_name = fields.Char(string='اسم مستلم العميل')
    customer_sign_date = fields.Date(string='تاريخ التسليم للعميل')
    customer_signature = fields.Binary(string='توقيع العميل')

    @api.model
    def _group_expand_state(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

    @api.depends('requisition_ids', 'receipt_ids')
    def _compute_doc_counts(self):
        for wo in self:
            wo.requisition_count = len(wo.requisition_ids)
            wo.receipt_count = len(wo.receipt_ids)

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
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                if vals.get('sale_order_id'):
                    so = self.env['sale.order'].browse(vals['sale_order_id'])
                    base = self._make_name_from_so(so.name)
                    # تفادي تكرار الرقم عند وجود أكثر من منتج مُصنّع في نفس أمر البيع
                    taken = self.search_count([('name', '=like', base + '%')])
                    vals['name'] = base if not taken else '%s-%d' % (base, taken + 1)
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        self._sequence_code) or 'New'
        return super().create(vals_list)

    # ----- أزرار سير العمل -----
    def action_confirm(self):
        for wo in self:
            if wo.state == 'draft':
                wo.state = 'confirmed'

    def action_request_materials(self):
        for wo in self:
            if wo.materials_available:
                raise UserError(_(
                    'المواد متوفرة بالمخزون، لا يمكن طلب مواد جديدة. انتقل مباشرة لاستلام المواد.'))
            if wo.state not in ('draft', 'confirmed'):
                raise UserError(_('لا يمكن طلب المواد في الحالة الحالية.'))
            req = self.env['rwasi.material.requisition'].create({
                'work_order_id': wo.id,
                'partner_id': wo.partner_id.id,
                'project_ref': wo.project_ref,
                'just_work_order': True,
            })
            for line in wo.line_ids:
                self.env['rwasi.material.requisition.line'].create({
                    'requisition_id': req.id,
                    'description': line.description,
                    'qty': line.qty,
                    'uom': line.uom,
                })
            wo.state = 'material_requested'
        return True

    def action_receive_materials(self):
        for wo in self:
            if wo.state == 'material_received':
                continue
            if not wo.materials_available and wo.state != 'material_requested':
                raise UserError(_('يجب طلب المواد أولاً قبل استلامها.'))
            if wo.state not in ('confirmed', 'material_requested'):
                raise UserError(_('لا يمكن استلام المواد في الحالة الحالية.'))
            self.env['rwasi.material.receipt'].create({
                'work_order_id': wo.id,
                'partner_id': wo.partner_id.id,
                'project_ref': wo.project_ref,
            })
            wo.state = 'material_received'
        return True

    def action_start_production(self):
        for wo in self:
            if wo.state != 'material_received':
                raise UserError(_('لا يمكن بدء التصنيع إلا بعد استلام المواد.'))
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
            wo.state = 'delivered'
            if not wo.customer_sign_date:
                wo.customer_sign_date = fields.Date.context_today(wo)
        return True

    def action_close(self):
        for wo in self:
            if wo.state != 'delivered':
                raise UserError(_('لا يمكن إغلاق الأمر إلا بعد التسليم للعميل.'))
            wo.state = 'done'
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات المواد'),
            'res_model': 'rwasi.material.requisition',
            'view_mode': 'list,form',
            'domain': [('work_order_id', '=', self.id)],
            'context': {'default_work_order_id': self.id},
        }

    def action_view_receipts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('استلام المواد'),
            'res_model': 'rwasi.material.receipt',
            'view_mode': 'list,form',
            'domain': [('work_order_id', '=', self.id)],
            'context': {'default_work_order_id': self.id},
        }


class WorkOrderLine(models.Model):
    _name = 'rwasi.work.order.line'
    _description = 'بند تنفيذ أمر التشغيل'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التشغيل', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    description = fields.Char(string='وصف البند', required=True)
    qty = fields.Float(string='الكمية', default=1.0)
    uom = fields.Char(string='الوحدة')
    item_ref = fields.Char(string='مرجع البند')
    status = fields.Char(string='الحالة')
