from odoo import models, fields


# ============================================================
# RS-WS-18 — اجتماع السلامة اليومي (HSE Toolbox Talk)
# ============================================================
class ToolboxTalk(models.Model):
    _name = 'rwasi.toolbox.talk'
    _description = 'اجتماع السلامة اليومي (RS-WS-18)'
    _inherit = ['rwasi.workshop.mixin', 'rwasi.signoff.mixin']
    _order = 'id desc'
    _sequence_code = 'rwasi.toolbox.talk'

    talk_date = fields.Date(string='التاريخ', default=fields.Date.context_today)
    workshop = fields.Char(string='الورشة')
    topic = fields.Char(string='الموضوع')
    presenter = fields.Char(string='المُلقي')

    key_points = fields.Text(string='النقاط الرئيسية للموضوع')

    # المخاطر المحددة
    hz_cuts = fields.Boolean(string='القطع والجروح')
    hz_fire = fields.Boolean(string='الحريق / اللحام')
    hz_electrical = fields.Boolean(string='الكهرباء')
    hz_fall = fields.Boolean(string='السقوط من ارتفاع')
    hz_lifting = fields.Boolean(string='الأحمال الثقيلة')
    hz_noise = fields.Boolean(string='الضوضاء والاهتزاز')
    hz_chemicals = fields.Boolean(string='الكيماويات')
    hz_heat = fields.Boolean(string='الحرارة')

    attendee_ids = fields.One2many(
        'rwasi.toolbox.attendee', 'talk_id', string='قائمة الحضور')

    # المُلقي / مسؤول السلامة
    hse_officer_name = fields.Char(string='مسؤول السلامة - الاسم')
    hse_officer_date = fields.Date(string='مسؤول السلامة - التاريخ')
    hse_officer_signature = fields.Binary(string='مسؤول السلامة - التوقيع')


class ToolboxAttendee(models.Model):
    _name = 'rwasi.toolbox.attendee'
    _description = 'حاضر اجتماع السلامة'
    _order = 'sequence, id'

    talk_id = fields.Many2one(
        'rwasi.toolbox.talk', required=True, ondelete='cascade')
    sequence = fields.Integer(string='م.', default=10)
    name = fields.Char(string='الاسم', required=True)
    id_no = fields.Char(string='رقم البصمة')
    trade = fields.Char(string='المهنة')
