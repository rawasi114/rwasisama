# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMaterialRequestBase(TransactionCase):
    """اختبارات قاعدة طلب المواد المجرّدة + معالج الـ PIN (المرحلة 3).

    السلوك الكامل لسير الاعتماد يُختبر مع النماذج الملموسة في موديولي
    المقاولات والورشة. هنا نختبر ما يمكن التحقق منه على المستوى المجرّد
    + معالج الـ PIN المشترك.
    """

    def test_abstract_model_registered(self):
        model = self.env["rawasi.material.request.base"]
        self.assertTrue(model._abstract, "يجب أن يكون النموذج مجرّداً (بلا جدول)")

    def test_states_defined(self):
        model = self.env["rawasi.material.request.base"]
        states = dict(model._fields["state"].selection)
        for key in (
            "draft",
            "approved_supervisor",
            "approved_budget",
            "in_purchase",
            "issued",
            "cancelled",
        ):
            self.assertIn(key, states)

    def test_require_pin_reads_config(self):
        model = self.env["rawasi.material.request.base"]
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("rawasi_base.require_pin_on_issue", "True")
        self.assertTrue(model._require_pin())
        icp.set_param("rawasi_base.require_pin_on_issue", "False")
        self.assertFalse(model._require_pin())

    def test_do_issue_not_implemented(self):
        model = self.env["rawasi.material.request.base"]
        with self.assertRaises(NotImplementedError):
            model._do_issue()

    def test_pin_wizard_wrong_pin_raises(self):
        self.env.user.pin_code = "654321"
        self.env.user.flush_recordset()
        wiz = self.env["rawasi.pin.wizard"].create(
            {
                "pin": "000000",
                "res_model": "res.partner",
                "res_id": self.env.user.partner_id.id,
                "method": "action_confirm",
            }
        )
        with self.assertRaises(UserError):
            wiz.action_confirm()

    def test_pin_wizard_no_pin_set_raises(self):
        self.env.user.pin_code = False
        self.env.user.flush_recordset()
        wiz = self.env["rawasi.pin.wizard"].create(
            {
                "pin": "123456",
                "res_model": "res.partner",
                "res_id": self.env.user.partner_id.id,
                "method": "action_confirm",
            }
        )
        with self.assertRaises(UserError):
            wiz.action_confirm()
