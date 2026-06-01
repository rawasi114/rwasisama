# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class RawasiPinWizard(models.TransientModel):
    """معالج تأكيد العمليات الحرجة بالـ PIN.

    مشترك بين المقاولات (الصرف من العهدة) والورشة (صرف مواد الإنتاج).
    يتحقق من PIN المستخدم الحالي ثم يستدعي الدالة المطلوبة على السجل الهدف
    مع تمرير السياق pin_verified=True.
    """

    _name = "rawasi.pin.wizard"
    _description = "تأكيد بالـ PIN — رواسي"

    pin = fields.Char(string="الرمز السري (PIN)", required=True)
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    method = fields.Char(required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.pin_code:
            raise UserError("لا يوجد PIN معرَّف لحسابك. اطلب من الأدمن تعيينه.")
        if not self.env.user.check_pin(self.pin):
            raise UserError("الـ PIN غير صحيح.")
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError("السجل الهدف لم يَعُد موجوداً.")
        return getattr(record.with_context(pin_verified=True), self.method)()
