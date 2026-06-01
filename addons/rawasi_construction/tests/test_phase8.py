# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


def _parse_tlv(data):
    out, i = {}, 0
    while i < len(data):
        tag = data[i]
        length = data[i + 1]
        out[tag] = data[i + 2:i + 2 + length].decode("utf-8")
        i += 2 + length
    return out


@tagged("post_install", "-at_install")
class TestPhase8(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.vat = "311111111111113"
        self.project = self.env["project.project"].create({"name": "مشروع م8"})
        self.comp = self.env["rawasi.competition"].create({
            "name": "منافسة م8", "project_id": self.project.id,
        })
        self.item = self.env["rawasi.boq.item"].create({
            "competition_id": self.comp.id, "name": "بند", "quantity": 10.0,
            "unit_cost": 80.0, "unit_price": 100.0,
        })

    # ── ZATCA: ترميز TLV + توليد QR ─────────────────────────────
    def test_zatca_qr_tlv(self):
        pc = self.env["rawasi.payment.certificate"].create({
            "project_id": self.project.id, "retention_pct": 10.0, "vat_rate": 15.0,
        })
        pc.action_generate_lines()
        pc.line_ids.work_qty = 4.0
        # work=400, retention=40, net=360, tax=54, total=414
        self.assertEqual(pc.amount_total, 414.0)
        self.assertTrue(pc.zatca_qr)
        tlv = _parse_tlv(base64.b64decode(pc.zatca_qr))
        self.assertEqual(tlv[2], "311111111111113")  # الرقم الضريبي
        self.assertEqual(tlv[4], "414.00")           # الإجمالي شامل الضريبة
        self.assertEqual(tlv[5], "54.00")            # مبلغ الضريبة
        self.assertEqual(tlv[1], self.env.company.name)
        self.assertTrue(pc.zatca_qr_image)           # صورة QR مولّدة

    # ── أمان: قيود الأدوار ──────────────────────────────────────
    def test_consultant_cannot_create_competition(self):
        cons = self.env["res.users"].create({
            "name": "استشاري", "login": "cons8",
            "group_ids": [(6, 0, [
                self.env.ref("rawasi_construction.group_external_consultant").id,
            ])],
        })
        with self.assertRaises(AccessError):
            self.env["rawasi.competition"].with_user(cons).create({"name": "x"})

    def test_site_engineer_no_purchase_order_access(self):
        site = self.env["res.users"].create({
            "name": "مهندس موقع", "login": "site8",
            "group_ids": [(6, 0, [
                self.env.ref("rawasi_construction.group_site_engineer").id,
            ])],
        })
        with self.assertRaises(AccessError):
            self.env["rawasi.purchase.order"].with_user(site).create({
                "project_id": self.project.id,
            })
