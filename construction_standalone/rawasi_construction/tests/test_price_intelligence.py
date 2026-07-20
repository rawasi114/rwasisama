# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPriceIntelligence(TransactionCase):
    def setUp(self):
        super().setUp()
        self.PI = self.env["rawasi.price.intelligence"]

    def _priced_competition(self, name, desc, unit_cost, unit_price):
        comp = self.env["rawasi.competition"].create({"name": name})
        self.env["rawasi.boq.item"].create({
            "competition_id": comp.id,
            "name": desc,
            "quantity": 100.0,
            "unit_cost": unit_cost,
            "unit_price": unit_price,
        })
        comp.action_start_pricing()
        comp.action_submit()
        return comp

    # ── الالتقاط التلقائي عند التقديم + تحديث النتيجة ─────────────
    def test_snapshot_on_submit_and_outcome(self):
        comp = self._priced_competition(
            "منافسة أ", "توريد وتركيب حديد تسليح قطر 16 مم", 50.0, 60.0
        )
        snaps = comp.price_intelligence_ids
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps.outcome, "submitted")
        self.assertEqual(snaps.unit_price, 60.0)
        self.assertTrue(snaps.name_normalized)
        comp.action_won()
        self.assertEqual(snaps.outcome, "won")

    def test_reset_removes_snapshots(self):
        comp = self._priced_competition("منافسة ب", "خرسانة مسلحة C30", 40.0, 48.0)
        self.assertEqual(len(comp.price_intelligence_ids), 1)
        comp.action_reset_to_draft()
        self.assertEqual(len(comp.price_intelligence_ids), 0)

    def test_unpriced_items_not_captured(self):
        comp = self.env["rawasi.competition"].create({"name": "منافسة ج"})
        self.env["rawasi.boq.item"].create({
            "competition_id": comp.id,
            "name": "بند بلا سعر",
            "quantity": 10.0,
            "unit_cost": 5.0,
            "unit_price": 0.0,
        })
        comp.action_start_pricing()
        comp.action_submit()
        self.assertEqual(len(comp.price_intelligence_ids), 0)

    # ── المطابقة الفجوية ─────────────────────────────────────────
    def test_fuzzy_match_finds_similar(self):
        self._priced_competition(
            "تاريخية", "توريد وتركيب حديد تسليح قطر 16 مم", 50.0, 60.0
        )
        # وصف مشابه بصياغة مختلفة وأرقام عربية
        matches = self.PI.search_matches("توريد و تركيب حديد التسليح قطر ١٦مم")
        self.assertTrue(matches, "يجب أن يجد تطابقاً فجوياً")
        best_score, best = matches[0]
        self.assertGreaterEqual(best_score, 0.7)
        self.assertEqual(best.unit_price, 60.0)

    def test_fuzzy_match_ignores_unrelated(self):
        self._priced_competition("تاريخية", "خرسانة مسلحة للأساسات", 40.0, 48.0)
        matches = self.PI.search_matches("تمديدات كهربائية وأسلاك نحاسية")
        self.assertFalse(matches, "لا يجب أن يطابق وصفاً غير متعلق")

    def test_exclude_same_competition(self):
        comp = self._priced_competition("نفسها", "عزل مائي للأسطح", 30.0, 36.0)
        # استبعاد منافسة المصدر يمنع مطابقة البند بنفسه
        matches = self.PI.search_matches(
            "عزل مائي للأسطح", exclude_competition_id=comp.id
        )
        self.assertFalse(matches)

    # ── تطبيق أفضل سعر على بند جديد ──────────────────────────────
    def test_apply_best_price(self):
        self._priced_competition("تاريخية", "دهان داخلي بلاستيك", 12.0, 15.0)
        new_comp = self.env["rawasi.competition"].create({"name": "جديدة"})
        item = self.env["rawasi.boq.item"].create({
            "competition_id": new_comp.id,
            "name": "دهان داخلي بلاستيك",
            "quantity": 500.0,
        })
        item.action_apply_best_price()
        self.assertEqual(item.unit_cost, 12.0)
        self.assertEqual(item.unit_price, 15.0)

    def test_apply_best_price_no_match_raises(self):
        new_comp = self.env["rawasi.competition"].create({"name": "جديدة"})
        item = self.env["rawasi.boq.item"].create({
            "competition_id": new_comp.id,
            "name": "بند فريد لا مثيل له",
            "quantity": 1.0,
        })
        with self.assertRaises(UserError):
            item.action_apply_best_price()

    def test_show_suggestions_action(self):
        self._priced_competition("تاريخية", "بلاط بورسلين 60×60", 80.0, 95.0)
        new_comp = self.env["rawasi.competition"].create({"name": "جديدة"})
        item = self.env["rawasi.boq.item"].create({
            "competition_id": new_comp.id,
            "name": "بلاط بورسلين 60×60",
            "quantity": 200.0,
        })
        action = item.action_show_price_suggestions()
        self.assertEqual(action["res_model"], "rawasi.price.intelligence")
        # الدومين يحوي معرفات المطابقات
        domain_ids = action["domain"][0][2]
        self.assertTrue(domain_ids)
