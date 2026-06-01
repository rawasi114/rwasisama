# -*- coding: utf-8 -*-
import base64
import io

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.pdf import PdfWriter, merge_pdf


def _make_pdf():
    """ينشئ بايتات PDF صالح بصفحة واحدة لاختبار الدمج."""
    writer = PdfWriter()
    if hasattr(writer, "add_blank_page"):
        writer.add_blank_page(width=200, height=200)
    else:  # pragma: no cover - توافق مع إصدار PyPDF2 الأقدم
        writer.addBlankPage(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@tagged("post_install", "-at_install")
class TestPhase4(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "مشروع المرحلة 4"})
        self.comp = self.env["rawasi.competition"].create({"name": "منافسة م4"})
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id,
            "name": "خرسانة مسلحة",
            "quantity": 10.0,
            "unit_cost": 100.0,
        })

    def _attach(self, mas, data, name="cat.pdf"):
        return self.env["ir.attachment"].create({
            "name": name,
            "datas": base64.b64encode(data),
            "mimetype": "application/pdf",
            "res_model": mas._name,
            "res_id": mas.id,
        })

    # ── MAS: القيد المعماري (بند BOQ إلزامي) ──────────────────────
    def test_mas_requires_boq_item(self):
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["rawasi.material.approval"].create({
                    "project_id": self.project.id,
                    "material_name": "بلا بند",
                })

    # ── MAS: التسلسل وسير العمل ──────────────────────────────────
    def test_mas_workflow_and_sequence(self):
        mas = self.env["rawasi.material.approval"].create({
            "project_id": self.project.id,
            "boq_item_id": self.item.id,
            "material_name": "حديد تسليح",
        })
        self.assertTrue(mas.name.startswith("MAS/"))
        self.assertEqual(mas.state, "draft")
        mas.action_submit()
        self.assertEqual(mas.state, "submitted")
        mas.action_approve_as_noted()
        self.assertEqual(mas.state, "approved_as_noted")
        mas.action_reset_to_draft()
        self.assertEqual(mas.state, "draft")

    # ── MAS: دمج PDF (الغلاف يحتاج wkhtmltopdf؛ هنا نختبر دمج المرفقات) ──
    def test_mas_pdf_merge(self):
        mas = self.env["rawasi.material.approval"].create({
            "project_id": self.project.id,
            "boq_item_id": self.item.id,
            "material_name": "عازل مائي",
        })
        a1 = self._attach(mas, _make_pdf(), "a.pdf")
        a2 = self._attach(mas, _make_pdf(), "b.pdf")
        # مرفق غير PDF يجب أن يُستبعد من الدمج
        self.env["ir.attachment"].create({
            "name": "note.txt",
            "datas": base64.b64encode(b"hello"),
            "mimetype": "text/plain",
            "res_model": mas._name,
            "res_id": mas.id,
        })
        mas.attachment_ids = [(6, 0, (a1 + a2).ids)]
        streams = mas._attachment_pdf_streams()
        self.assertEqual(len(streams), 2)
        merged = merge_pdf(streams)
        self.assertTrue(merged[:4] == b"%PDF")

    # ── DMS: التسلسل وسير العمل ──────────────────────────────────
    def test_document_workflow(self):
        doc = self.env["rawasi.document"].create({
            "name": "مخطط معماري",
            "project_id": self.project.id,
            "document_type": "drawing",
        })
        self.assertTrue(doc.reference.startswith("DOC/"))
        doc.action_submit_review()
        self.assertEqual(doc.state, "under_review")
        doc.action_approve()
        self.assertEqual(doc.state, "approved")

    # ── DSR: التسلسل + احتساب إجمالي العمالة ─────────────────────
    def test_dsr_total_workers(self):
        dsr = self.env["rawasi.daily.report"].create({
            "project_id": self.project.id,
            "labor_ids": [
                (0, 0, {"trade": "نجار", "worker_count": 5}),
                (0, 0, {"trade": "حداد", "worker_count": 3}),
            ],
        })
        self.assertTrue(dsr.name.startswith("DSR/"))
        self.assertEqual(dsr.total_workers, 8)
        dsr.action_confirm()
        self.assertEqual(dsr.state, "confirmed")

    # ── NCR: بند BOQ اختياري + إغلاق يسجّل التاريخ ───────────────
    def test_ncr_workflow(self):
        ncr = self.env["rawasi.ncr"].create({
            "project_id": self.project.id,
            "subject": "صبّة لا تطابق المواصفات",
            "description": "مقاومة أقل من المطلوب",
            "severity": "major",
        })
        self.assertTrue(ncr.name.startswith("NCR/"))
        self.assertFalse(ncr.boq_item_id)  # اختياري
        ncr.action_start()
        self.assertEqual(ncr.state, "in_progress")
        ncr.action_close()
        self.assertEqual(ncr.state, "closed")
        self.assertTrue(ncr.closed_date)

    # ── RFI: الرد إلزامي قبل الوسم كمُجاب ────────────────────────
    def test_rfi_answer_required(self):
        rfi = self.env["rawasi.rfi"].create({
            "project_id": self.project.id,
            "subject": "تفاصيل التأسيس",
            "question": "ما عمق القواعد؟",
        })
        self.assertTrue(rfi.name.startswith("RFI/"))
        rfi.action_submit()
        with self.assertRaises(UserError):
            rfi.action_answer()
        rfi.answer = "العمق 2 متر"
        rfi.action_answer()
        self.assertEqual(rfi.state, "answered")
        self.assertTrue(rfi.date_answered)
