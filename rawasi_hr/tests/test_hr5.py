# -*- coding: utf-8 -*-
import base64
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestEosSettlement(TransactionCase):
    """اختبارات احتساب مكافأة نهاية الخدمة (المواد 84/85/87)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Settlement = cls.env["rawasi.eos.settlement"]
        cls.employee = cls.env["hr.employee"].create({
            "name": "موظف اختبار",
            "rawasi_basic_wage": 8000.0,
            "rawasi_housing_allowance": 2000.0,
        })

    def _make(self, start, end, reason, wage=10000.0):
        return self.Settlement.create({
            "employee_id": self.employee.id,
            "start_date": start,
            "end_date": end,
            "reason": reason,
            "wage_base": wage,
        })

    def test_sequence_assigned(self):
        s = self._make(date(2020, 1, 1), date(2024, 1, 1), "termination")
        self.assertNotEqual(s.name, "جديد", "يجب توليد مرجع تسلسلي")

    def test_termination_under_5_years(self):
        # 4 سنوات بالضبط، إنهاء من صاحب العمل: نصف شهر لكل سنة = 4×0.5 = 2 شهر
        s = self._make(date(2020, 1, 1), date(2024, 1, 1), "termination")
        self.assertAlmostEqual(s.service_years, 1461 / 365.0, places=2)
        # ~4.0 سنة → 2 × الأجر تقريباً
        self.assertAlmostEqual(s.gratuity_amount, s.wage_base * 0.5 * s.service_years, places=2)
        self.assertEqual(s.entitlement_ratio, 1.0)

    def test_termination_over_5_years(self):
        # 10 سنوات: أول 5 بنصف شهر (2.5) + 5 بشهر كامل (5) = 7.5 شهر
        s = self._make(date(2010, 1, 1), date(2020, 1, 1), "termination")
        years = s.service_years
        expected_months = min(years, 5) * 0.5 + max(years - 5, 0) * 1.0
        self.assertAlmostEqual(s.gratuity_full, s.wage_base * expected_months, places=2)
        self.assertAlmostEqual(s.gratuity_amount, s.gratuity_full, places=2)

    def test_resignation_under_2_years_zero(self):
        s = self._make(date(2023, 1, 1), date(2024, 6, 1), "resignation")
        self.assertLess(s.service_years, 2.0)
        self.assertEqual(s.entitlement_ratio, 0.0)
        self.assertEqual(s.gratuity_amount, 0.0)

    def test_resignation_2_to_5_third(self):
        s = self._make(date(2020, 1, 1), date(2023, 6, 1), "resignation")
        self.assertTrue(2.0 <= s.service_years < 5.0)
        self.assertAlmostEqual(s.entitlement_ratio, 1.0 / 3.0, places=4)
        self.assertAlmostEqual(s.gratuity_amount, s.gratuity_full / 3.0, places=2)

    def test_resignation_5_to_10_two_thirds(self):
        s = self._make(date(2014, 1, 1), date(2021, 1, 1), "resignation")
        self.assertTrue(5.0 <= s.service_years < 10.0)
        self.assertAlmostEqual(s.entitlement_ratio, 2.0 / 3.0, places=4)

    def test_resignation_over_10_full(self):
        s = self._make(date(2008, 1, 1), date(2020, 1, 1), "resignation")
        self.assertGreaterEqual(s.service_years, 10.0)
        self.assertEqual(s.entitlement_ratio, 1.0)
        self.assertAlmostEqual(s.gratuity_amount, s.gratuity_full, places=2)

    def test_special_full_overrides_resignation(self):
        # حالة المادة 87: استحقاق كامل رغم قصر المدة
        s = self._make(date(2023, 1, 1), date(2024, 6, 1), "special_full")
        self.assertEqual(s.entitlement_ratio, 1.0)

    def test_dismissal_80_zero(self):
        s = self._make(date(2010, 1, 1), date(2020, 1, 1), "dismissal_80")
        self.assertEqual(s.entitlement_ratio, 0.0)
        self.assertEqual(s.gratuity_amount, 0.0)

    def test_net_amount_with_dues_and_deductions(self):
        s = self._make(date(2015, 1, 1), date(2020, 1, 1), "termination")
        s.leave_balance_amount = 5000.0
        s.other_dues = 1000.0
        s.deductions = 2000.0
        expected = s.gratuity_amount + 5000.0 + 1000.0 - 2000.0
        self.assertAlmostEqual(s.net_amount, expected, places=2)

    def test_invalid_dates_raise(self):
        with self.assertRaises(ValidationError):
            self._make(date(2020, 1, 1), date(2019, 1, 1), "termination")

    def test_onchange_pulls_wage(self):
        s = self.Settlement.new({"employee_id": self.employee.id})
        s._onchange_employee_id()
        self.assertEqual(s.wage_base, 10000.0)

    def test_confirm_requires_wage(self):
        s = self._make(date(2020, 1, 1), date(2024, 1, 1), "termination", wage=0.0)
        with self.assertRaises(UserError):
            s.action_confirm()

    def test_state_flow(self):
        s = self._make(date(2015, 1, 1), date(2020, 1, 1), "termination")
        s.action_confirm()
        self.assertEqual(s.state, "confirmed")
        s.action_mark_paid()
        self.assertEqual(s.state, "paid")


class TestWpsBatch(TransactionCase):
    """اختبارات دفعة حماية الأجور وتوليد ملف SIF."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.rawasi_mol_establishment_id = "1-12345678"
        cls.emp1 = cls.env["hr.employee"].create({
            "name": "أحمد",
            "rawasi_basic_wage": 6000.0,
            "rawasi_housing_allowance": 1500.0,
            "rawasi_bank_iban": "SA0380000000608010167519",
            "rawasi_mol_number": "111",
        })
        cls.emp2 = cls.env["hr.employee"].create({
            "name": "خالد",
            "rawasi_basic_wage": 5000.0,
            "rawasi_bank_iban": "SA4420000001234567891234",
            "rawasi_mol_number": "222",
        })

    def test_populate_and_totals(self):
        batch = self.env["rawasi.wps.batch"].create({"month": "6", "year": 2026})
        batch.action_populate_lines()
        self.assertGreaterEqual(len(batch.line_ids), 2)
        self.assertEqual(batch.employee_count, len(batch.line_ids))
        # صافي emp1 = 6000 + 1500 = 7500
        line1 = batch.line_ids.filtered(lambda l: l.employee_id == self.emp1)
        self.assertAlmostEqual(line1.net_salary, 7500.0, places=2)

    def test_generate_file(self):
        batch = self.env["rawasi.wps.batch"].create({"month": "6", "year": 2026})
        batch.action_populate_lines()
        batch.action_generate_file()
        self.assertEqual(batch.state, "generated")
        self.assertTrue(batch.sif_file)
        content = base64.b64decode(batch.sif_file).decode("utf-8-sig")
        self.assertIn("EMPLOYER", content)
        self.assertIn("1-12345678", content)
        self.assertIn("SA0380000000608010167519", content)

    def test_generate_requires_establishment(self):
        self.company.rawasi_mol_establishment_id = False
        batch = self.env["rawasi.wps.batch"].create({"month": "6", "year": 2026})
        batch.action_populate_lines()
        with self.assertRaises(UserError):
            batch.action_generate_file()

    def test_generate_requires_iban(self):
        self.emp2.rawasi_bank_iban = False
        batch = self.env["rawasi.wps.batch"].create({"month": "6", "year": 2026})
        batch.action_populate_lines()
        with self.assertRaises(UserError):
            batch.action_generate_file()
