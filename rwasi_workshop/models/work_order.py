import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .base import WORKSHOP_SCOPE


class WorkOrder(models.Model):
    """RS-WS-01 — أمر تشغيل / أمر تصنيع (النموذج المركزي لدورة الحياة المغلقة)."""
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

    # المواد وفحص التوفر بالمخزون
    material_line_ids = fields.One2many(
        'rwasi.work.order.material', 'order_id', string='المواد اللازمة')
    materials_available = fields.Boolean(
        string='المواد متوفرة بالمخزون', compute='_compute_materials_available',
        help='يُحتسب تلقائياً من الكمية المتاحة بالمخزون لكل مادة.')

    # الشراء والتسليم (دورة مغلقة)
    purchase_order_ids = fields.One2many(
        'purchase.order', 'workshop_order_id', string='طلبات الشراء')
    purchase_order_count = fields.Integer(compute='_compute_counts')
    has_draft_rfq = fields.Boolean(compute='_compute_purchase_flow')
    has_rfq_to_confirm = fields.Boolean(compute='_compute_purchase_flow')
    has_pending_receipt = fields.Boolean(compute='_compute_purchase_flow')
    delivery_note_id = fields.Many2one(
        'rwasi.delivery.note', string='أمر التسليم', readonly=True, copy=False)
    delivery_count = fields.Integer(compute='_compute_counts')
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
    ], string='الحالة', default='draft', tracking=True, group_expand='_group_expand_state')

    # تسليم العميل
    customer_sign_name = fields.Char(string='اسم مستلم العميل')
    customer_sign_date = fields.Date(string='تاريخ التسليم للعميل')
    customer_signature = fields.Binary(string='توقيع العميل')

    @api.model
    def _group_expand_state(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

    @api.depends('material_line_ids.is_available')
    def _compute_materials_available(self):
        for wo in self:
            wo.materials_available = all(
                line.is_available for line in wo.material_line_ids)

    @api.depends('purchase_order_ids', 'delivery_note_id', 'closeout_id')
    def _compute_counts(self):
        for wo in self:
            wo.purchase_order_count = len(wo.purchase_order_ids)
            wo.delivery_count = 1 if wo.delivery_note_id else 0
            wo.closeout_count = 1 if wo.closeout_id else 0

    @api.depends('purchase_order_ids', 'purchase_order_ids.state')
    def _compute_purchase_flow(self):
        for wo in self:
            pos = wo.purchase_order_ids
            wo.has_draft_rfq = any(p.state == 'draft' for p in pos)
            wo.has_rfq_to_confirm = any(p.state in ('draft', 'sent') for p in pos)
            pending = False
            for p in pos.filtered(lambda x: x.state in ('purchase', 'done')):
                if any(pk.state not in ('done', 'cancel') for pk in p.picking_ids):
                    pending = True
                    break
            wo.has_pending_receipt = pending

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
        # لا يُنشأ أمر التصنيع إلا تلقائياً عند تأكيد عرض السعر (أمر البيع)
        if not self.env.context.get('from_sale_order'):
            raise UserError(_(
                'لا يمكن إنشاء أمر تصنيع يدوياً. '
                'يُنشأ أمر التصنيع تلقائياً فقط عند تأكيد عرض السعر للمنتجات المعلَّمة بأنها تُصنّع في الورشة.'))
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                if vals.get('sale_order_id'):
                    so = self.env['sale.order'].browse(vals['sale_order_id'])
                    base = self._make_name_from_so(so.name)
                    taken = self.search_count([('name', '=like', base + '%')])
                    vals['name'] = base if not taken else '%s-%d' % (base, taken + 1)
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        self._sequence_code) or 'New'
        return super().create(vals_list)

    # ----- أزرار سير العمل (دورة مغلقة) -----
    def _get_placeholder_vendor(self):
        """مورّد مبدئي يُستخدم للمواد التي لم يُحدَّد لها مورّد بعد (يغيّره المشتري)."""
        Partner = self.env['res.partner'].sudo()
        vendor = Partner.search(
            [('name', '=', 'مورّد يُحدَّد لاحقاً')], limit=1)
        if not vendor:
            vendor = Partner.create({
                'name': 'مورّد يُحدَّد لاحقاً',
                'company_type': 'company',
                'supplier_rank': 1,
            })
        return vendor

    def action_request_materials(self):
        """ينشئ طلب عرض أسعار (RFQ) في موديول الشراء للمواد الناقصة.
        لا يُجبر على تحديد مورّد: المواد بلا مورّد تُجمَّع في طلب بمورّد مبدئي."""
        for wo in self:
            if wo.materials_available:
                raise UserError(_(
                    'المواد متوفرة بالمخزون، لا يمكن طلب مواد جديدة. يمكنك تأكيد أمر التصنيع مباشرة.'))
            shortages = wo.material_line_ids.filtered(lambda l: not l.is_available)
            if not shortages:
                raise UserError(_('لا توجد مواد ناقصة لطلبها.'))

            by_vendor = {}
            no_vendor_lines = []
            for line in shortages:
                # الأولوية للمورّد المختار يدوياً في سطر المادة، ثم مورّد المنتج
                vendor = line.vendor_id or line.material_id.seller_ids[:1].partner_id
                if vendor:
                    by_vendor.setdefault(vendor, []).append(line)
                else:
                    no_vendor_lines.append(line)
            if no_vendor_lines:
                by_vendor.setdefault(wo._get_placeholder_vendor(), []).extend(
                    no_vendor_lines)

            PurchaseOrder = self.env['purchase.order'].sudo()
            warehouse = wo.company_id.sudo().workshop_warehouse_id
            for vendor, lines in by_vendor.items():
                order_lines = []
                for l in lines:
                    deficit = l.qty_needed - l.qty_available
                    qty = deficit if deficit > 0 else l.qty_needed
                    order_lines.append((0, 0, {
                        'product_id': l.material_id.id,
                        'product_qty': qty,
                    }))
                po_vals = {
                    'partner_id': vendor.id,
                    'origin': wo.name,
                    'workshop_order_id': wo.id,
                    'order_line': order_lines,
                }
                # عزل مخزون الورشة: توجيه الاستلام لمستودع الورشة إن حُدّد
                if warehouse and warehouse.in_type_id:
                    po_vals['picking_type_id'] = warehouse.in_type_id.id
                PurchaseOrder.create(po_vals)
            wo.message_post(body=_('تم إنشاء طلب/طلبات عرض سعر (RFQ) للمواد الناقصة.'))
        return True

    def action_send_rfq(self):
        """إرسال طلبات عرض السعر (تحويلها إلى حالة «مُرسَل») من داخل الورشة."""
        for wo in self:
            pos = wo.purchase_order_ids.sudo().filtered(lambda p: p.state == 'draft')
            if not pos:
                raise UserError(_('لا توجد طلبات عرض سعر بحالة مسودة لإرسالها.'))
            pos.write({'state': 'sent'})
            wo.message_post(body=_('تم إرسال طلب/طلبات عرض السعر للمورّدين.'))
        return True

    def action_confirm_purchase(self):
        """تأكيد طلبات الشراء (RFQ → أمر شراء) من داخل الورشة، وإنشاء عمليات الاستلام."""
        for wo in self:
            pos = wo.purchase_order_ids.sudo().filtered(
                lambda p: p.state in ('draft', 'sent'))
            if not pos:
                raise UserError(_('لا توجد طلبات لتأكيدها.'))
            for po in pos:
                po.button_confirm()
            wo.message_post(body=_('تم تأكيد طلب/طلبات الشراء وإنشاء عمليات الاستلام.'))
        return True

    def action_receive_materials(self):
        """يستلم المواد من داخل الورشة بتأكيد طلبات الشراء وترحيل عمليات الاستلام
        (يُنشئ حركة استلام فعلية في المخزون دون مغادرة الورشة)."""
        for wo in self:
            if wo.materials_available:
                continue
            pos = wo.purchase_order_ids.sudo()
            if not pos:
                raise UserError(_('اطلب المواد أولاً عبر زر «طلب المواد (شراء)».'))
            for po in pos.filtered(lambda p: p.state in ('draft', 'sent')):
                po.button_confirm()
            pickings = pos.mapped('picking_ids').filtered(
                lambda p: p.state not in ('done', 'cancel'))
            if not pickings:
                raise UserError(_(
                    'لا توجد عمليات استلام للترحيل. تأكد أن المواد المطلوبة من نوع '
                    '«قابل للتخزين» (Storable) لكي يُنشئ نظام الشراء إيصال استلام لها.'))
            for picking in pickings:
                picking.sudo().action_confirm()
                picking.sudo().action_assign()
                for move in picking.sudo().move_ids:
                    if 'quantity' in move._fields:
                        move.quantity = move.product_uom_qty
                    elif 'quantity_done' in move._fields:
                        move.quantity_done = move.product_uom_qty
                    if 'picked' in move._fields:
                        move.picked = True
                res = picking.sudo().with_context(
                    skip_backorder=True, skip_sms=True).button_validate()
                # أودو قد يُعيد نافذة تأكيد بدل الترحيل المباشر — نعالجها برمجياً
                if isinstance(res, dict) and res.get('res_model'):
                    wiz_model = res['res_model']
                    wiz_ctx = dict(res.get('context') or {})
                    wizard = self.env[wiz_model].sudo().with_context(
                        wiz_ctx).create({})
                    for method in ('process', 'process_cancel_backorder'):
                        if hasattr(wizard, method):
                            getattr(wizard, method)()
                            break
            wo.material_line_ids.invalidate_recordset(
                ['qty_available', 'is_available'])
            if not wo.materials_available:
                raise UserError(_(
                    'تم ترحيل الاستلام لكن الكمية المتاحة لا تزال غير كافية. '
                    'راجع كميات المواد المطلوبة أو إعدادات المخزون لهذه المواد.'))
            wo.message_post(body=_('تم استلام المواد وترحيلها إلى المخزون.'))
        return True

    def action_confirm(self):
        for wo in self:
            if wo.state != 'draft':
                continue
            if not wo.materials_available:
                raise UserError(_(
                    'لا يمكن تأكيد أمر التصنيع قبل توفّر المواد بالمخزون أو استلامها.'))
            wo.state = 'confirmed'
        return True

    def action_start_production(self):
        for wo in self:
            if wo.state != 'confirmed':
                raise UserError(_('يجب تأكيد أمر التصنيع أولاً قبل بدء التصنيع.'))
            wo.state = 'in_production'
            if not wo.start_date:
                wo.start_date = fields.Date.context_today(wo)
        return True

    def action_finish_production(self):
        for wo in self:
            if wo.state != 'in_production':
                raise UserError(_('لا يمكن إنهاء التصنيع إلا أثناء التصنيع.'))
            wo.state = 'finished'
            wo._create_delivery_note()
        return True

    def _create_delivery_note(self):
        self.ensure_one()
        if self.delivery_note_id:
            return
        note = self.env['rwasi.delivery.note'].sudo().with_context(
            from_work_order=True).create({
                'work_order_id': self.id,
                'partner_id': self.partner_id.id,
                'site': self.project_ref,
                'consignee': self.partner_id.name,
            })
        self.delivery_note_id = note.id
        self.message_post(body=_('تم إنشاء أمر التسليم %s عند إنهاء التصنيع.') % note.name)

    def action_deliver(self):
        for wo in self:
            if wo.state != 'finished':
                raise UserError(_('لا يمكن التسليم إلا بعد إنهاء التصنيع.'))
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
        co = self.env['rwasi.project.closeout'].create({
            'work_order_id': self.id,
            'partner_id': self.partner_id.id,
            'project_ref': self.project_ref,
            'customer_sign_name': self.customer_sign_name,
            'handover_date': fields.Date.context_today(self),
        })
        self.closeout_id = co.id
        self.message_post(body=_('تم إنشاء استبيان إغلاق المشروع %s.') % co.name)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    # ----- أزرار ذكية -----
    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات الشراء'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('workshop_order_id', '=', self.id)],
        }

    def action_view_delivery(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('أمر التسليم'),
            'res_model': 'rwasi.delivery.note',
            'view_mode': 'form,list',
            'res_id': self.delivery_note_id.id,
        }

    def action_view_closeout(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إغلاق المشروع'),
            'res_model': 'rwasi.project.closeout',
            'view_mode': 'form,list',
            'res_id': self.closeout_id.id,
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


class WorkOrderMaterial(models.Model):
    _name = 'rwasi.work.order.material'
    _description = 'مادة لازمة لأمر التصنيع'
    _order = 'id'

    order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع', required=True, ondelete='cascade')
    material_id = fields.Many2one(
        'product.product', string='المادة الخام', required=True)
    vendor_id = fields.Many2one(
        'res.partner', string='المورّد',
        help='يُستخدم عند إنشاء طلب عرض السعر. اتركه فارغاً ليُحدَّد لاحقاً.')
    qty_needed = fields.Float(string='الكمية المطلوبة', default=1.0)
    qty_available = fields.Float(
        string='المتوفر بالمخزون', compute='_compute_availability')
    is_available = fields.Boolean(
        string='متوفرة', compute='_compute_availability')
    uom_name = fields.Char(related='material_id.uom_id.name', string='الوحدة')

    @api.depends('material_id', 'qty_needed')
    def _compute_availability(self):
        for line in self:
            product = line.material_id
            if not product:
                line.qty_available = 0.0
                line.is_available = False
                continue
            # عزل مخزون الورشة: احسب التوفر في مستودع الورشة إن حُدّد، وإلا المخزون العام
            location = line.order_id.company_id.sudo().workshop_warehouse_id.lot_stock_id
            if location:
                avail = product.with_context(location=location.id).qty_available
            else:
                avail = product.qty_available
            line.qty_available = avail
            line.is_available = avail >= line.qty_needed
