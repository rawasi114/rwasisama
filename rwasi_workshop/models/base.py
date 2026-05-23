from odoo import models, fields, api

# قسم التنفيذ المشترك بين نماذج الورشة
WORKSHOP_SCOPE = [
    ('carpentry', 'نجارة'),
    ('steel', 'حدادة'),
    ('aluminum', 'ألمنيوم'),
    ('cnc', 'CNC'),
]


class WorkshopMixin(models.AbstractModel):
    """حقول الترويسة المشتركة لجميع نماذج الورشة."""
    _name = 'rwasi.workshop.mixin'
    _description = 'ترويسة نماذج الورشة'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # كود التسلسل لكل نموذج يُعرّف في النموذج الوريث
    _sequence_code = None

    name = fields.Char(
        string='رقم النموذج / المرجع', required=True, copy=False,
        readonly=True, index=True, default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string='العميل', tracking=True)
    project_ref = fields.Char(string='المشروع')
    project_code = fields.Char(string='كود المشروع')
    date_issued = fields.Date(
        string='تاريخ الإصدار', default=fields.Date.context_today, tracking=True)
    revision = fields.Char(string='المراجعة', default='R0')
    company_id = fields.Many2one(
        'res.company', string='الشركة', default=lambda self: self.env.company)
    note = fields.Text(string='ملاحظات')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self._sequence_code and vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    self._sequence_code) or 'New'
        return super().create(vals_list)


class SignoffMixin(models.AbstractModel):
    """كتل التوقيع والاعتماد المشتركة (تُعاد تسميتها في كل نموذج عند الحاجة)."""
    _name = 'rwasi.signoff.mixin'
    _description = 'كتل اعتماد نماذج الورشة'

    prepared_name = fields.Char(string='معد النموذج - الاسم')
    prepared_date = fields.Date(string='معد النموذج - التاريخ')
    prepared_phone = fields.Char(string='معد النموذج - الهاتف')
    prepared_signature = fields.Binary(string='معد النموذج - التوقيع')

    supervisor_name = fields.Char(string='مشرف الورشة - الاسم')
    supervisor_date = fields.Date(string='مشرف الورشة - التاريخ')
    supervisor_section = fields.Char(string='مشرف الورشة - القسم')
    supervisor_signature = fields.Binary(string='مشرف الورشة - التوقيع')

    manager_name = fields.Char(string='مدير العمليات - الاسم')
    manager_date = fields.Date(string='مدير العمليات - التاريخ')
    manager_signature = fields.Binary(string='مدير العمليات - التوقيع')
    manager_stamp = fields.Binary(string='ختم الشركة')
