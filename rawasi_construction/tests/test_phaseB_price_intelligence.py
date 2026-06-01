# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPhaseBPriceIntelligence(TransactionCase):
    """اختبارات المرحلة B: ذاكرة الأسعار + المطابقة الفجوية + الالتقاط من المنافسة."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "أمانة الرياض"})
        cls.ref = cls.env["rawasi.reference.item"].create(
            {"name": "خرسانة مسلحة C35", "category": "civil", "standard_cost": 250.0}
        )
        cls.uom = cls.ref.uom_id

    def _make_submitted_competition(self, title, price):
        comp = self.env["rawasi.competition"].create(
            {"title": title, "partner_id": self.partner.id}
        )
        self.env["rawasi.boq.item"].create(
            {
                "competition_id": comp.id,
                "reference_item_id": self.ref.id,
                "description": "توريد وصب خرسانة مسلحة للأساسات",
                "uom_id": self.uom.id,
                "qty": 100,
                "unit_cost": 250,
                "unit_price": 300,
            }
        )
        comp.action_set_pricing()
        comp.action_submit()
        return comp

    def test_capture_on_submit(self):
        comp = self._make_submitted_competition("مبنى إداري", 300)
        recs = self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", comp.id)]
        )
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs.unit_price, 300)
        self.assertEqual(recs.outcome, "submitted")
        self.assertTrue(recs.name_normalized)

    def test_margin_computed(self):
        comp = self._make_submitted_competition("فيلا", 300)
        rec = self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", comp.id)], limit=1
        )
        self.assertAlmostEqual(rec.margin_pct, (300 - 250) / 250 * 100.0)

    def test_outcome_updates_on_won(self):
        comp = self._make_submitted_competition("مستودع", 300)
        comp.action_won()
        rec = self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", comp.id)], limit=1
        )
        self.assertEqual(rec.outcome, "won")

    def test_outcome_updates_on_lost(self):
        comp = self._make_submitted_competition("جسر", 300)
        comp.action_lost()
        rec = self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", comp.id)], limit=1
        )
        self.assertEqual(rec.outcome, "lost")

    def test_search_matches_finds_similar(self):
        self._make_submitted_competition("سابق", 300)
        matches = self.env["rawasi.price.intelligence"].search_matches(
            "توريد وصب خرسانة مسلحة للاساسات", uom_id=self.uom.id
        )
        self.assertTrue(matches, "يجب أن تُرجع مطابقات لوصف مشابه")
        top_score, top_rec = matches[0]
        self.assertGreaterEqual(top_score, 0.5)
        self.assertEqual(top_rec.unit_price, 300)

    def test_search_matches_empty_text(self):
        self.assertEqual(
            self.env["rawasi.price.intelligence"].search_matches(""), []
        )

    def test_resubmit_replaces_snapshot(self):
        comp = self._make_submitted_competition("إعادة", 300)
        comp.action_lost()
        comp.action_reset_draft()
        comp.action_set_pricing()
        comp.action_submit()
        recs = self.env["rawasi.price.intelligence"].search(
            [("competition_id", "=", comp.id)]
        )
        self.assertEqual(len(recs), 1, "إعادة التقديم تستبدل اللقطة لا تكررها")
