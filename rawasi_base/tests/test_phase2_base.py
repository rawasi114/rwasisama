# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestRawasiBase(TransactionCase):
    """اختبارات أساس rawasi_base (المرحلتان 1 و 2)."""

    def test_equipment_sequence_and_create(self):
        eq = self.env["rawasi.equipment"].create({"name": "هايلكس", "category": "vehicle"})
        self.assertTrue(eq.code, "يجب توليد رمز تلقائي للأصل")
        self.assertIn(eq.category, dict(eq._fields["category"].selection))

    def test_chart_of_accounts_loaded(self):
        # عيّنة من شجرة الحسابات الـ 272 يجب أن تكون محمَّلة
        acc = self.env.ref("rawasi_base.coa_411100", raise_if_not_found=False)
        self.assertTrue(acc, "حساب إيرادات مشاريع المقاولات يجب أن يكون محمَّلاً")
        self.assertEqual(acc.account_type, "income")
        # الحساب الذي صُحِّح نوعه
        fixed = self.env.ref("rawasi_base.coa_71031", raise_if_not_found=False)
        self.assertTrue(fixed)
        self.assertEqual(fixed.account_type, "expense")

    def test_analytic_plans(self):
        plan = self.env.ref("rawasi_base.analytic_plan_rawasi", raise_if_not_found=False)
        self.assertTrue(plan)
        children = self.env["account.analytic.plan"].search([("parent_id", "=", plan.id)])
        self.assertGreaterEqual(len(children), 2, "خطتا المقاولات والورشة")

    def test_document_and_folder(self):
        folder = self.env["rawasi.document.folder"].create({"name": "عقود"})
        child = self.env["rawasi.document.folder"].create(
            {"name": "2026", "parent_id": folder.id}
        )
        self.assertEqual(child.complete_name, "عقود / 2026")
        doc = self.env["rawasi.document"].create(
            {
                "name": "عقد المشروع",
                "folder_id": child.id,
                "file": base64.b64encode(b"hello"),
                "file_name": "contract.txt",
            }
        )
        self.assertTrue(doc.is_current_version)
        self.assertEqual(child.document_count, 1)

    def test_audit_trail_append_only(self):
        eq = self.env["rawasi.equipment"].create(
            {"name": "منشار", "category": "workshop_machine"}
        )
        audit = self.env["rawasi.audit.trail"].log(eq, "override", reason="اختبار")
        self.assertEqual(audit.event, "override")
        self.assertEqual(audit.model_name, "rawasi.equipment")
        self.assertEqual(audit.res_id, eq.id)
        rec = self.env["rawasi.audit.trail"].browse(audit.id)
        with self.assertRaises(UserError):
            rec.write({"reason": "تعديل ممنوع"})
            rec.flush_recordset()
        with self.assertRaises(UserError):
            rec.unlink()

    def test_pin_validation(self):
        user = self.env["res.users"].create({"name": "فني", "login": "fani_pin_test"})
        with self.assertRaises(ValidationError):
            user.pin_code = "123"
            user.flush_recordset()
        user.pin_code = "123456"
        user.flush_recordset()
        self.assertTrue(user.check_pin("123456"))
        self.assertFalse(user.check_pin("000000"))

    def test_approval_chain(self):
        chain = self.env["rawasi.approval.chain"].create(
            {"name": "اعتماد طلب مواد", "model": "rawasi.material.request"}
        )
        self.env["rawasi.approval.step"].create(
            {
                "chain_id": chain.id,
                "name": "اعتماد المشرف",
                "group_id": self.env.ref("rawasi_base.group_rawasi_accountant").id,
            }
        )
        self.assertEqual(len(chain.step_ids), 1)

    def test_notification_hook_posts_chatter(self):
        folder = self.env["rawasi.document.folder"].create({"name": "f"})
        doc = self.env["rawasi.document"].create(
            {
                "name": "d",
                "folder_id": folder.id,
                "file": base64.b64encode(b"x"),
                "file_name": "x.txt",
            }
        )
        before = len(doc.message_ids)
        res = self.env["rawasi.notification.hook"].send(doc, "approval_overdue")
        self.assertTrue(res)
        self.assertGreater(len(doc.message_ids), before)

    def test_cron_escalation_safe(self):
        # يجب ألا يفشل حتى مع عدم وجود نشاطات متأخرة
        self.env["rawasi.approval.chain"]._cron_escalate_overdue()

    def test_shared_groups_inheritance(self):
        admin = self.env.ref("rawasi_base.group_rawasi_admin")
        accountant = self.env.ref("rawasi_base.group_rawasi_accountant")
        # الأدمن يرث مدير الحسابات
        self.assertIn(accountant, admin.implied_ids)
