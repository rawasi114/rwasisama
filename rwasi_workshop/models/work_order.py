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

    # الربط بأمر البيع (1:1 — كل أمر بيع له أمر تصنيع واحد فقط؛
    # بنود المنتجات الورشية المتعددة في SO تصبح work_jobs داخل هذا الـ MO)
    sale_order_id = fields.Many2one(
        'sale.order', string='أمر البيع', readonly=True, copy=False, index=True)
    product_id = fields.Many2one(
        'product.product', string='المنتج الرئيسي',
        help='يُحفظ كمرجع عام؛ المنتجات الفعلية للتصنيع تظهر في بنود التنفيذ (work jobs).')
    product_qty = fields.Float(string='الكمية', default=1.0)

    _uniq_sale_order = models.Constraint(
        'unique (sale_order_id)',
        'يوجد بالفعل أمر تصنيع لأمر البيع هذا. كل أمر بيع له أمر تصنيع واحد فقط؛ '
        'أضف منتجات إضافية كبنود تنفيذ (work jobs) داخل أمر التصنيع القائم.',
    )

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
    # اعتماد طلب المواد: مشرف الورشة ← الحسابات ← المشتريات
    material_approval_state = fields.Selection([
        ('draft', 'لم يُطلب'),
        ('to_approve', 'بانتظار مشرف الورشة'),
        ('to_finance', 'بانتظار اعتماد الحسابات'),
        ('approved', 'معتمد ومُرسل للمشتريات'),
        ('rejected', 'مرفوض'),
        ('to_revise', 'يحتاج تعديل'),
    ], string='اعتماد طلب المواد', default='draft', tracking=True, copy=False)
    material_approval_reason = fields.Text(string='سبب الرفض / الإعادة', copy=False)
    material_approver_id = fields.Many2one(
        'res.users', string='معتمِد المواد', readonly=True, copy=False)
    # الإسناد والإشعارات والتسليم
    material_approver_assignee_id = fields.Many2one(
        'res.users', string='مشرف الورشة المُسنَد', copy=False,
        help='يُسنده الفنّي عند رفع الطلب؛ يصله إشعار ليعتمد الطلب فنيّاً.')
    finance_user_id = fields.Many2one(
        'res.users', string='موظف الحسابات (التمويل)', copy=False,
        help='يُسنده مشرف الورشة عند اعتماده الطلب؛ يصله إشعار لاعتماد التمويل.')
    finance_approver_id = fields.Many2one(
        'res.users', string='معتمِد التمويل', readonly=True, copy=False)
    finance_approval_date = fields.Date(
        string='تاريخ اعتماد التمويل', readonly=True, copy=False)
    purchase_user_id = fields.Many2one(
        'res.users', string='موظف المشتريات', copy=False,
        help='يُسنده موظف الحسابات بعد اعتماد التمويل؛ ينفّذ الشراء.')
    can_approve_materials = fields.Boolean(compute='_compute_user_flags')
    can_handle_finance = fields.Boolean(compute='_compute_user_flags')
    can_handle_purchase = fields.Boolean(compute='_compute_user_flags')
    material_handover_done = fields.Boolean(
        string='تم تسليم المواد للورشة', readonly=True, copy=False)
    material_handover_date = fields.Date(
        string='تاريخ تسليم المواد', readonly=True, copy=False)
    material_received_by = fields.Char(string='مستلم المواد (الورشة)', copy=False)
    material_handover_signature = fields.Binary(
        string='توقيع مستلم المواد', copy=False)
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

    # حالة السداد (تتحدّث تلقائياً من فواتير أمر البيع — بلا أرقام مالية)
    payment_status = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئي'),
        ('paid', 'مدفوع بالكامل'),
    ], string='حالة السداد', compute='_compute_payment_status')
    paid_ratio = fields.Float(
        string='نسبة السداد', compute='_compute_payment_status',
        help='نسبة المسدَّد من قيمة الفاتورة (للتحكّم الداخلي).')

    # تسليم العميل
    customer_sign_name = fields.Char(string='اسم مستلم العميل')
    customer_sign_date = fields.Date(string='تاريخ التسليم للعميل')
    customer_signature = fields.Binary(string='توقيع العميل')

    @api.model
    def _group_expand_state(self, *args, **kwargs):
        return [s[0] for s in self._fields['state'].selection]

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

    @api.depends('material_line_ids.is_available')
    def _compute_materials_available(self):
        for wo in self:
            wo.materials_available = bool(wo.material_line_ids) and all(
                line.is_available for line in wo.material_line_ids)

    @api.depends('purchase_order_ids', 'closeout_id')
    def _compute_counts(self):
        for wo in self:
            wo.purchase_order_count = len(wo.purchase_order_ids)
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

    def write(self, vals):
        # أمر التصنيع المغلق نهائي: لا يُعاد فتحه أو تغيير حالته بأي مسار
        if 'state' in vals and vals['state'] != 'done':
            locked = self.filtered(lambda w: w.state == 'done')
            if locked:
                raise UserError(_(
                    'لا يمكن تغيير حالة أمر تصنيع مغلق. '
                    'أنشئ أمراً جديداً إن لزم الأمر.'))
        return super().write(vals)

    # ----- أزرار سير العمل (دورة مغلقة) -----
    @api.depends_context('uid')
    @api.depends('material_approver_assignee_id', 'finance_user_id', 'purchase_user_id')
    def _compute_user_flags(self):
        user = self.env.user
        is_mgr = (user.has_group('rwasi_workshop.group_workshop_manager')
                  or self.env.is_superuser())
        for wo in self:
            wo.can_approve_materials = is_mgr or (
                wo.material_approver_assignee_id.id == user.id)
            wo.can_handle_finance = is_mgr or (
                wo.finance_user_id.id == user.id)
            wo.can_handle_purchase = is_mgr or (
                wo.purchase_user_id.id == user.id)

    def _ensure_can_approve(self):
        if not self.can_approve_materials:
            raise UserError(_(
                'الاعتماد الفنّي متاح لمشرف الورشة المُسنَد أو المدير فقط.'))

    def _ensure_can_handle_finance(self):
        if not self.can_handle_finance:
            raise UserError(_(
                'اعتماد التمويل متاح لموظف الحسابات المُسنَد أو المدير فقط.'))

    def action_open_submit_wizard(self):
        self.ensure_one()
        if not self.material_line_ids:
            raise UserError(_('أضف قائمة المواد (المكوّنات) أولاً.'))
        if self.paid_ratio < 0.5:
            raise UserError(_(
                'لا يمكن طلب المواد قبل سداد دفعة لا تقل عن 50% من قيمة الطلب.'))
        self._check_materials_storable()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إسناد طلب اعتماد المواد'),
            'res_model': 'rwasi.wo.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_work_order_id': self.id,
                'default_mode': 'submit',
                'default_user_id': self.material_approver_assignee_id.id or False,
            },
        }

    def action_open_approve_wizard(self):
        self.ensure_one()
        self._ensure_can_approve()
        return {
            'type': 'ir.actions.act_window',
            'name': _('اعتماد الطلب وإرساله للحسابات'),
            'res_model': 'rwasi.wo.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_work_order_id': self.id,
                'default_mode': 'approve',
                'default_user_id': self.finance_user_id.id or False,
            },
        }

    def action_open_finance_wizard(self):
        self.ensure_one()
        self._ensure_can_handle_finance()
        return {
            'type': 'ir.actions.act_window',
            'name': _('اعتماد التمويل وإسناد المشتريات'),
            'res_model': 'rwasi.wo.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_work_order_id': self.id,
                'default_mode': 'finance',
                'default_user_id': self.purchase_user_id.id or False,
            },
        }

    def action_submit_materials(self):
        """يرفع مشرف الورشة طلب المواد لاعتماد المسؤول المُسنَد إليه."""
        for wo in self:
            if not wo.material_line_ids:
                raise UserError(_('أضف قائمة المواد (المكوّنات) أولاً.'))
            if wo.paid_ratio < 0.5:
                raise UserError(_(
                    'لا يمكن طلب المواد قبل سداد دفعة لا تقل عن 50% من قيمة الطلب.'))
            wo._check_materials_storable()
            if not wo.material_approver_assignee_id:
                raise UserError(_(
                    'أسند الطلب إلى مستخدم مسؤول (للاعتماد) قبل رفعه.'))
            wo.material_approval_state = 'to_approve'
            wo.material_approval_reason = False
            wo.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=wo.material_approver_assignee_id.id,
                summary=_('اعتماد طلب مواد'),
                note=_('طلب مواد بانتظار اعتمادك لأمر التصنيع %s.') % wo.name)
            wo.message_post(body=_('تم رفع طلب المواد لاعتماد المسؤول (%s).')
                            % wo.material_approver_assignee_id.name)
        return True

    def action_approve_materials(self):
        """اعتماد مشرف الورشة للطلب فنّياً وإرساله للحسابات لتمويل المشتريات."""
        for wo in self:
            wo._ensure_can_approve()
            if wo.material_approval_state != 'to_approve':
                continue
            if not wo.finance_user_id:
                raise UserError(_(
                    'حدّد موظف الحسابات (المُسنَد إليه) قبل اعتماد الطلب.'))
            wo.material_approval_state = 'to_finance'
            wo.material_approver_id = self.env.user
            wo.material_approval_reason = False
            wo.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=wo.finance_user_id.id,
                summary=_('اعتماد تمويل طلب مواد'),
                note=_('طلب مواد بانتظار اعتمادك مالياً (توفير السيولة) '
                       'لأمر التصنيع %s.') % wo.name)
            wo.message_post(body=_(
                'اعتمد مشرف الورشة الطلب فنّياً وأرسله للحسابات (%s) لتمويل المشتريات.')
                % wo.finance_user_id.name)
        return True

    def action_finance_approve(self):
        """اعتماد الحسابات للتمويل وإسناد المشتريات + إنشاء طلب الشراء."""
        for wo in self:
            wo._ensure_can_handle_finance()
            if wo.material_approval_state != 'to_finance':
                continue
            if not wo.purchase_user_id:
                raise UserError(_(
                    'حدّد موظف المشتريات (المُسنَد إليه) قبل اعتماد التمويل.'))
            wo.material_approval_state = 'approved'
            wo.finance_approver_id = self.env.user
            wo.finance_approval_date = fields.Date.context_today(wo)
            wo.material_approval_reason = False
            # المستلِم للمواد عند تسليمها للورشة = المعتمِد الفنّي (يُعدَّل عند الحاجة)
            if not wo.material_received_by:
                wo.material_received_by = (
                    wo.material_approver_id.name or self.env.user.name)
            wo._create_material_rfq()
            wo.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=wo.purchase_user_id.id,
                summary=_('تنفيذ شراء مواد'),
                note=_('اعتمدت الحسابات تمويل طلب المواد لأمر التصنيع %s. '
                       'أكمل طلب الشراء من تطبيق المشتريات ثم سلّم المواد للورشة.')
                % wo.name)
            wo.message_post(body=_(
                'اعتمدت الحسابات التمويل وأرسلت الطلب إلى موظف المشتريات (%s).')
                % wo.purchase_user_id.name)
        return True

    def _decide_actor(self):
        """يحدّد الجهة (مشرف/حسابات) المخوّلة بالرفض/الإعادة حسب الحالة الحالية."""
        self.ensure_one()
        if self.material_approval_state == 'to_approve':
            self._ensure_can_approve()
            self.material_approver_id = self.env.user
            return 'مشرف الورشة'
        if self.material_approval_state == 'to_finance':
            self._ensure_can_handle_finance()
            self.finance_approver_id = self.env.user
            return 'الحسابات'
        return None

    def action_reject_materials(self):
        for wo in self:
            actor = wo._decide_actor()
            if not actor:
                continue
            if not wo.material_approval_reason:
                raise UserError(_('اكتب سبب الرفض في حقل «سبب الرفض / الإعادة» أولاً.'))
            wo.material_approval_state = 'rejected'
            wo.message_post(body=_('رفض %s طلب المواد. السبب: %s')
                            % (actor, wo.material_approval_reason))
        return True

    def action_revise_materials(self):
        for wo in self:
            actor = wo._decide_actor()
            if not actor:
                continue
            if not wo.material_approval_reason:
                raise UserError(_('اكتب سبب الإعادة في حقل «سبب الرفض / الإعادة» أولاً.'))
            wo.material_approval_state = 'to_revise'
            wo.message_post(body=_('أعاد %s طلب المواد للتعديل. السبب: %s')
                            % (actor, wo.material_approval_reason))
        return True

    def _create_material_rfq(self):
        """ينشئ طلب شراء مسودة مربوطاً بأمر التصنيع باسم موظف المشتريات
        (يكمله ويستلمه من تطبيق المشتريات الرئيسي)."""
        self.ensure_one()
        shortages = self.material_line_ids.filtered(lambda l: not l.is_available)
        if not shortages:
            return
        by_vendor = {}
        no_vendor = []
        for line in shortages:
            vendor = line.vendor_id or line.material_id.seller_ids[:1].partner_id
            if vendor:
                by_vendor.setdefault(vendor, []).append(line)
            else:
                no_vendor.append(line)
        if no_vendor:
            by_vendor.setdefault(self._get_placeholder_vendor(), []).extend(no_vendor)
        PurchaseOrder = self.env['purchase.order'].sudo()
        warehouse = self.company_id.sudo().workshop_warehouse_id
        for vendor, lines in by_vendor.items():
            order_lines = []
            for l in lines:
                deficit = l.qty_needed - l.qty_available
                qty = deficit if deficit > 0 else l.qty_needed
                order_lines.append((0, 0, {
                    'product_id': l.material_id.id,
                    'product_qty': qty,
                }))
            vals = {
                'partner_id': vendor.id,
                'origin': self.name,
                'workshop_order_id': self.id,
                'order_line': order_lines,
            }
            if self.purchase_user_id:
                vals['user_id'] = self.purchase_user_id.id
            if warehouse and warehouse.in_type_id:
                vals['picking_type_id'] = warehouse.in_type_id.id
            PurchaseOrder.create(vals)

    def action_handover_materials(self):
        """موظف المشتريات يسلّم المواد للورشة ويأخذ توقيع المستلم."""
        for wo in self:
            if not (wo.can_handle_purchase or self.env.is_superuser()):
                raise UserError(_(
                    'تسليم المواد للورشة متاح لموظف المشتريات المُسنَد أو المدير فقط.'))
            if not wo.material_received_by:
                raise UserError(_('اكتب اسم مستلم المواد من الورشة.'))
            if not wo.material_handover_signature:
                raise UserError(_('التقط توقيع مستلم المواد.'))
            wo.material_handover_done = True
            wo.material_handover_date = fields.Date.context_today(wo)
            wo.message_post(body=_('تم تسليم المواد للورشة واستلامها بواسطة %s.')
                            % wo.material_received_by)
        return True

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

    def _check_materials_storable(self):
        """تتأكد أن مكوّنات أمر التصنيع قابلة للتخزين حتى يُتتبّع مخزونها."""
        self.ensure_one()
        bad = self.material_line_ids.filtered(lambda l: l.material_id and not (
            l.material_id.is_storable if 'is_storable' in l.material_id._fields
            else l.material_id.type == 'product'))
        if bad:
            names = '\n- '.join(bad.mapped('material_id.display_name'))
            raise UserError(_(
                'المواد التالية غير قابلة للتخزين فلا يُتتبّع مخزونها. '
                'فعّل «تتبّع المخزون» في بطاقة كل منها:\n- %s') % names)

    def action_request_materials(self):
        """ينشئ طلب عرض أسعار (RFQ) في موديول الشراء للمواد الناقصة.
        لا يُجبر على تحديد مورّد: المواد بلا مورّد تُجمَّع في طلب بمورّد مبدئي."""
        for wo in self:
            if not wo.material_line_ids:
                raise UserError(_(
                    'أضف قائمة المواد (المكوّنات) أولاً في تبويب «المواد اللازمة».'))
            if wo.paid_ratio < 0.5:
                raise UserError(_(
                    'لا يمكن طلب المواد قبل سداد دفعة لا تقل عن 50% من قيمة الطلب.'))
            if wo.material_approval_state != 'approved':
                raise UserError(_(
                    'طلب المواد يحتاج اعتماد مدير المبيعات والورش أولاً.'))
            wo._check_materials_storable()
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
            wo.invalidate_recordset(['materials_available'])
            # لا نرفع خطأ بعد الترحيل (وإلا أُلغيت عملية الاستلام بالكامل)
            if wo.materials_available:
                wo.message_post(body=_('تم استلام المواد وأصبحت متوفرة بالمخزون.'))
            else:
                wo.message_post(body=_(
                    'تم ترحيل الاستلام. إن لم يظهر زر «تأكيد التصنيع» فقد تكون بعض '
                    'المواد ما زالت في موقع «الوارد» (استلام متعدّد الخطوات) أو الكمية ناقصة.'))
        return True

    def action_confirm(self):
        for wo in self:
            if wo.state != 'draft':
                continue
            if not wo.material_line_ids:
                raise UserError(_(
                    'لا يمكن تأكيد أمر تصنيع بلا قائمة مواد. '
                    'أضف المكوّنات في تبويب «المواد اللازمة» أولاً.'))
            wo._check_materials_storable()
            if not wo.materials_available:
                raise UserError(_(
                    'بعض المواد غير متوفرة بالمخزون. اطلبها عبر «إنشاء طلب عرض سعر» '
                    'ثم استلمها قبل تأكيد التصنيع.'))
            wo.state = 'confirmed'
        return True

    def action_start_production(self):
        for wo in self:
            if wo.state != 'confirmed':
                raise UserError(_('يجب تأكيد أمر التصنيع أولاً قبل بدء التصنيع.'))
            if wo.paid_ratio < 0.5:
                raise UserError(_(
                    'لا يمكن بدء التصنيع قبل سداد دفعة أولى لا تقل عن 50% من قيمة الفاتورة.'))
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
                    'لا يمكن الانتقال لمرحلة التسليم قبل سداد كامل قيمة العمل. '
                    'الحالة الحالية للسداد: غير مكتملة — بانتظار إغلاق الفاتورة من المحاسبة.'))
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
        self.message_post(body=_('تم إنشاء استبيان إغلاق المشروع %s.') % co.name)

    def action_cancel(self):
        for wo in self:
            if wo.state in ('delivered', 'done'):
                raise UserError(_(
                    'لا يمكن إلغاء أمر بعد التسليم للعميل أو الإغلاق.'))
            wo.state = 'cancel'

    def action_draft(self):
        for wo in self:
            if wo.state in ('delivered', 'done'):
                raise UserError(_(
                    'لا يمكن إعادة أمر مُسلَّم أو مغلق إلى مسودة.'))
            wo.state = 'draft'

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
    _description = 'بند تنفيذ أمر التشغيل (أمر عمل / Work Job)'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التشغيل', required=True, ondelete='cascade')
    # ربط الـ work job ببند أمر البيع الذي أنشأه (للتتبع 1:1 على مستوى البند)
    sale_line_id = fields.Many2one(
        'sale.order.line', string='بند أمر البيع', readonly=True, copy=False, index=True)
    product_id = fields.Many2one(
        'product.product', string='المنتج المُصنَّع',
        help='المنتج الذي يخصّ هذا الـ work job داخل أمر التصنيع.')
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
        'product.product', string='المادة الخام', required=True,
        domain=[('purchase_ok', '=', True), ('sale_ok', '=', False)])
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
            # عزل مخزون الورشة: احسب التوفر في كامل موقع مستودع الورشة إن حُدّد
            # (يشمل الوارد والمخزون لتغطية الاستلام متعدّد الخطوات)، وإلا المخزون العام
            location = line.order_id.company_id.sudo().workshop_warehouse_id.view_location_id
            if location:
                avail = product.with_context(location=location.id).qty_available
            else:
                avail = product.qty_available
            line.qty_available = avail
            line.is_available = avail >= line.qty_needed


class WorkOrderAssignWizard(models.TransientModel):
    _name = 'rwasi.wo.assign.wizard'
    _description = 'إسناد طلب المواد'

    work_order_id = fields.Many2one('rwasi.work.order', required=True)
    mode = fields.Selection([
        ('submit', 'إسناد للمشرف'),
        ('approve', 'إسناد للحسابات'),
        ('finance', 'إسناد للمشتريات'),
    ], required=True)
    user_id = fields.Many2one(
        'res.users', string='المُسنَد إليه', required=True,
        domain="[('share', '=', False)]")
    note = fields.Char(compute='_compute_note')

    _MODE_NOTES = {
        'submit': 'اختر مشرف الورشة الذي سيعتمد طلب المواد فنّياً (يصله إشعار).',
        'approve': 'اختر موظف الحسابات الذي سيعتمد التمويل ويوفّر السيولة (يصله إشعار).',
        'finance': 'اختر موظف المشتريات الذي سينفّذ الشراء (يصله إشعار).',
    }

    @api.depends('mode')
    def _compute_note(self):
        for w in self:
            w.note = self._MODE_NOTES.get(w.mode, '')

    def action_confirm(self):
        self.ensure_one()
        wo = self.work_order_id
        if self.mode == 'submit':
            wo.material_approver_assignee_id = self.user_id
            wo.action_submit_materials()
        elif self.mode == 'approve':
            wo.finance_user_id = self.user_id
            wo.action_approve_materials()
        else:  # finance
            wo.purchase_user_id = self.user_id
            wo.action_finance_approve()
        return {'type': 'ir.actions.act_window_close'}
