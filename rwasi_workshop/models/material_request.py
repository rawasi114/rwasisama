from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaterialRequest(models.Model):
    """طلب مواد لأمر تصنيع — قابل للتكرار لنفس أمر العمل."""
    _name = 'rwasi.material.request'
    _description = 'طلب مواد'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='رقم الطلب', default='New', readonly=True, copy=False, index=True)
    work_order_id = fields.Many2one(
        'rwasi.work.order', string='أمر التصنيع', required=True,
        ondelete='cascade', index=True)
    work_job_id = fields.Many2one(
        'rwasi.work.job', string='أمر العمل', required=True,
        domain="[('work_order_id', '=', work_order_id)]",
        help='حدّد أمر العمل (المنتج) الذي ستُستخدم له هذه المواد.')
    sale_order_id = fields.Many2one(
        related='work_order_id.sale_order_id', store=True)
    partner_id = fields.Many2one(
        related='work_order_id.partner_id', store=True)
    company_id = fields.Many2one(
        related='work_order_id.company_id', store=True)
    paid_ratio = fields.Float(related='work_order_id.paid_ratio')

    request_date = fields.Date(
        string='تاريخ الطلب', default=fields.Date.context_today, readonly=True)
    reason = fields.Selection([
        ('initial', 'طلب أولي'),
        ('additional', 'طلب إضافي'),
        ('replacement', 'تعويض هالك / تالف'),
    ], string='سبب الطلب', default='initial', required=True)
    note = fields.Text(string='ملاحظات')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('to_approve', 'بانتظار مشرف الورشة'),
        ('to_finance', 'بانتظار اعتماد الحسابات'),
        ('approved', 'معتمد ومُرسل للمشتريات'),
        ('rejected', 'مرفوض'),
        ('to_revise', 'يحتاج تعديل'),
        ('handover_done', 'مُسلَّم للورشة'),
        ('cancel', 'ملغي'),
    ], default='draft', tracking=True, copy=False)

    line_ids = fields.One2many(
        'rwasi.material.request.line', 'request_id', string='المواد المطلوبة')
    materials_available = fields.Boolean(
        string='كل المواد متوفرة', compute='_compute_materials_available')

    # الإسناد والاعتمادات
    material_approver_assignee_id = fields.Many2one(
        'res.users', string='مشرف الورشة المُسنَد', copy=False)
    material_approver_id = fields.Many2one(
        'res.users', string='معتمِد المشرف', readonly=True, copy=False)
    finance_user_id = fields.Many2one(
        'res.users', string='موظف الحسابات (التمويل)', copy=False)
    finance_approver_id = fields.Many2one(
        'res.users', string='معتمِد التمويل', readonly=True, copy=False)
    finance_approval_date = fields.Date(
        string='تاريخ اعتماد التمويل', readonly=True, copy=False)
    purchase_user_id = fields.Many2one(
        'res.users', string='موظف المشتريات', copy=False)
    approval_reason = fields.Text(string='سبب الرفض / الإعادة', copy=False)
    can_approve_materials = fields.Boolean(compute='_compute_user_flags')
    can_handle_finance = fields.Boolean(compute='_compute_user_flags')
    can_handle_purchase = fields.Boolean(compute='_compute_user_flags')

    # الشراء والتسليم
    purchase_order_ids = fields.One2many(
        'purchase.order', 'material_request_id', string='طلبات الشراء')
    purchase_order_count = fields.Integer(compute='_compute_po_count')
    material_handover_done = fields.Boolean(
        string='تم تسليم المواد للورشة', readonly=True, copy=False)
    material_handover_date = fields.Date(
        string='تاريخ تسليم المواد', readonly=True, copy=False)
    material_received_by = fields.Char(string='مستلم المواد (الورشة)', copy=False)
    material_handover_signature = fields.Binary(
        string='توقيع المستلم', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rwasi.material.request') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.is_available')
    def _compute_materials_available(self):
        for r in self:
            r.materials_available = bool(r.line_ids) and all(
                l.is_available for l in r.line_ids)

    @api.depends('purchase_order_ids')
    def _compute_po_count(self):
        for r in self:
            r.purchase_order_count = len(r.purchase_order_ids)

    @api.depends_context('uid')
    @api.depends('material_approver_assignee_id', 'finance_user_id', 'purchase_user_id')
    def _compute_user_flags(self):
        user = self.env.user
        is_mgr = (user.has_group('rwasi_workshop.group_workshop_manager')
                  or self.env.is_superuser())
        for r in self:
            r.can_approve_materials = is_mgr or (
                r.material_approver_assignee_id.id == user.id)
            r.can_handle_finance = is_mgr or (
                r.finance_user_id.id == user.id)
            r.can_handle_purchase = is_mgr or (
                r.purchase_user_id.id == user.id)

    # ---------------- بوّابات وحارسات ----------------
    def _ensure_can_approve(self):
        if not self.can_approve_materials:
            raise UserError(_(
                'الاعتماد الفنّي متاح لمشرف الورشة المُسنَد أو المدير فقط.'))

    def _ensure_can_handle_finance(self):
        if not self.can_handle_finance:
            raise UserError(_(
                'اعتماد التمويل متاح لموظف الحسابات المُسنَد أو المدير فقط.'))

    def _check_materials_storable(self):
        self.ensure_one()
        bad = self.line_ids.filtered(lambda l: l.material_id and not (
            l.material_id.is_storable if 'is_storable' in l.material_id._fields
            else l.material_id.type == 'product'))
        if bad:
            names = '\n- '.join(bad.mapped('material_id.display_name'))
            raise UserError(_(
                'المواد التالية غير قابلة للتخزين فلا يُتتبّع مخزونها. '
                'فعّل «تتبّع المخزون» في بطاقة كل منها:\n- %s') % names)

    # ---------------- معالجات (Wizards) ----------------
    def _open_wizard(self, mode, default_user):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إسناد طلب المواد'),
            'res_model': 'rwasi.material.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_mode': mode,
                'default_user_id': default_user.id if default_user else False,
            },
        }

    def action_open_submit_wizard(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('أضف بنود المواد أولاً.'))
        if self.paid_ratio < 0.5:
            raise UserError(_(
                'لا يمكن طلب المواد قبل سداد دفعة لا تقل عن 50% من قيمة أمر البيع.'))
        self._check_materials_storable()
        return self._open_wizard('submit', self.material_approver_assignee_id)

    def action_open_approve_wizard(self):
        self._ensure_can_approve()
        return self._open_wizard('approve', self.finance_user_id)

    def action_open_finance_wizard(self):
        self._ensure_can_handle_finance()
        return self._open_wizard('finance', self.purchase_user_id)

    # ---------------- الأحداث الفعلية ----------------
    def action_submit_materials(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('أضف بنود المواد أولاً.'))
            if r.paid_ratio < 0.5:
                raise UserError(_(
                    'لا يمكن طلب المواد قبل سداد ≥ 50% من قيمة أمر البيع.'))
            r._check_materials_storable()
            if not r.material_approver_assignee_id:
                raise UserError(_('أسند الطلب إلى مشرف ورشة قبل رفعه.'))
            r.state = 'to_approve'
            r.approval_reason = False
            r.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=r.material_approver_assignee_id.id,
                summary=_('اعتماد طلب مواد'),
                note=_('طلب مواد %s بانتظار اعتمادك لأمر التصنيع %s.')
                % (r.name, r.work_order_id.name))
            r.message_post(body=_('رُفع الطلب لاعتماد مشرف الورشة (%s).')
                           % r.material_approver_assignee_id.name)
        return True

    def action_approve_materials(self):
        for r in self:
            r._ensure_can_approve()
            if r.state != 'to_approve':
                continue
            if not r.finance_user_id:
                raise UserError(_('حدّد موظف الحسابات قبل اعتماد الطلب.'))
            r.state = 'to_finance'
            r.material_approver_id = self.env.user
            r.approval_reason = False
            r.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=r.finance_user_id.id,
                summary=_('اعتماد تمويل طلب مواد'),
                note=_('طلب %s بانتظار اعتماد التمويل (توفير السيولة).') % r.name)
            r.message_post(body=_(
                'اعتمد مشرف الورشة الطلب وأرسله للحسابات (%s) لتمويل المشتريات.')
                % r.finance_user_id.name)
        return True

    def action_finance_approve(self):
        for r in self:
            r._ensure_can_handle_finance()
            if r.state != 'to_finance':
                continue
            if not r.purchase_user_id:
                raise UserError(_('حدّد موظف المشتريات قبل اعتماد التمويل.'))
            r.state = 'approved'
            r.finance_approver_id = self.env.user
            r.finance_approval_date = fields.Date.context_today(r)
            r.approval_reason = False
            if not r.material_received_by:
                r.material_received_by = (
                    r.material_approver_id.name or self.env.user.name)
            r._create_material_rfq()
            r.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=r.purchase_user_id.id,
                summary=_('تنفيذ شراء مواد'),
                note=_('اعتمدت الحسابات تمويل طلب %s. أكمل الشراء ثم سلّم '
                       'المواد للورشة.') % r.name)
            r.message_post(body=_(
                'اعتمدت الحسابات التمويل وأرسلت الطلب إلى المشتريات (%s).')
                % r.purchase_user_id.name)
        return True

    def _decide_actor(self):
        self.ensure_one()
        if self.state == 'to_approve':
            self._ensure_can_approve()
            self.material_approver_id = self.env.user
            return 'مشرف الورشة'
        if self.state == 'to_finance':
            self._ensure_can_handle_finance()
            self.finance_approver_id = self.env.user
            return 'الحسابات'
        return None

    def action_reject_materials(self):
        for r in self:
            actor = r._decide_actor()
            if not actor:
                continue
            if not r.approval_reason:
                raise UserError(_('اكتب سبب الرفض أولاً.'))
            r.state = 'rejected'
            r.message_post(body=_('رفض %s الطلب. السبب: %s')
                           % (actor, r.approval_reason))
        return True

    def action_revise_materials(self):
        for r in self:
            actor = r._decide_actor()
            if not actor:
                continue
            if not r.approval_reason:
                raise UserError(_('اكتب سبب الإعادة أولاً.'))
            r.state = 'to_revise'
            r.message_post(body=_('أعاد %s الطلب للتعديل. السبب: %s')
                           % (actor, r.approval_reason))
        return True

    def action_handover_materials(self):
        for r in self:
            if not (r.can_handle_purchase or self.env.is_superuser()):
                raise UserError(_(
                    'تسليم المواد للورشة متاح لموظف المشتريات أو المدير فقط.'))
            if r.state != 'approved':
                continue
            if not r.material_received_by:
                raise UserError(_('اكتب اسم مستلم المواد من الورشة.'))
            if not r.material_handover_signature:
                raise UserError(_('التقط توقيع المستلم.'))
            r.state = 'handover_done'
            r.material_handover_done = True
            r.material_handover_date = fields.Date.context_today(r)
            r.message_post(body=_('سُلّمت المواد للورشة واستلمها %s.')
                           % r.material_received_by)
        return True

    def action_cancel(self):
        for r in self:
            if r.state in ('approved', 'handover_done'):
                raise UserError(_(
                    'لا يمكن إلغاء طلب أُنشئ له RFQ أو تم تسليم مواده.'))
            r.state = 'cancel'

    def action_draft(self):
        for r in self:
            if r.state in ('approved', 'handover_done'):
                raise UserError(_(
                    'لا يمكن إعادة طلب اعتُمد ماليّاً أو سُلّم إلى مسودة.'))
            r.state = 'draft'

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات الشراء'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('material_request_id', '=', self.id)],
        }

    # ---------------- إنشاء RFQ ----------------
    def _create_material_rfq(self):
        """ينشئ RFQ في الشراء للمواد الناقصة لهذا الطلب."""
        self.ensure_one()
        shortages = self.line_ids.filtered(lambda l: not l.is_available)
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
                'origin': '%s / %s' % (self.work_order_id.name, self.name),
                'material_request_id': self.id,
                'order_line': order_lines,
            }
            if self.purchase_user_id:
                vals['user_id'] = self.purchase_user_id.id
            if warehouse and warehouse.in_type_id:
                vals['picking_type_id'] = warehouse.in_type_id.id
            PurchaseOrder.create(vals)

    def _get_placeholder_vendor(self):
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


class MaterialRequestLine(models.Model):
    _name = 'rwasi.material.request.line'
    _description = 'بند طلب مواد'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'rwasi.material.request', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one(
        'product.product', string='المادة الخام', required=True,
        domain=[('purchase_ok', '=', True), ('sale_ok', '=', False)])
    vendor_id = fields.Many2one(
        'res.partner', string='المورّد',
        help='اتركه فارغاً ليُحدَّد لاحقاً.')
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
            location = line.request_id.company_id.sudo().workshop_warehouse_id.view_location_id
            if location:
                avail = product.with_context(location=location.id).qty_available
            else:
                avail = product.qty_available
            line.qty_available = avail
            line.is_available = avail >= line.qty_needed


class MaterialRequestWizard(models.TransientModel):
    """معالج إسناد لطلب المواد (٣ أوضاع): مشرف / حسابات / مشتريات."""
    _name = 'rwasi.material.request.wizard'
    _description = 'إسناد طلب المواد'

    request_id = fields.Many2one('rwasi.material.request', required=True)
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
        'submit': 'اختر مشرف الورشة الذي سيعتمد الطلب فنّياً (يصله إشعار).',
        'approve': 'اختر موظف الحسابات الذي سيعتمد التمويل ويوفّر السيولة (يصله إشعار).',
        'finance': 'اختر موظف المشتريات الذي سينفّذ الشراء (يصله إشعار).',
    }

    @api.depends('mode')
    def _compute_note(self):
        for w in self:
            w.note = self._MODE_NOTES.get(w.mode, '')

    def action_confirm(self):
        self.ensure_one()
        r = self.request_id
        if self.mode == 'submit':
            r.material_approver_assignee_id = self.user_id
            r.action_submit_materials()
        elif self.mode == 'approve':
            r.finance_user_id = self.user_id
            r.action_approve_materials()
        else:
            r.purchase_user_id = self.user_id
            r.action_finance_approve()
        return {'type': 'ir.actions.act_window_close'}
