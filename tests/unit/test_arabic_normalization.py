"""Arabic text normalization unit tests."""

import pytest

from api.utils.arabic import normalize_arabic, normalize_unit, units_compatible


class TestArabicNormalization:
    def test_strips_tashkeel(self):
        assert normalize_arabic("خَرَسَانَة") == "خرسانه"

    def test_unifies_alif_variants(self):
        assert normalize_arabic("أبواب") == normalize_arabic("ابواب")
        assert normalize_arabic("إنشاء") == normalize_arabic("انشاء")
        assert normalize_arabic("آلة") == normalize_arabic("اله")

    def test_unifies_ya_variants(self):
        assert normalize_arabic("علي") == normalize_arabic("على")

    def test_collapses_whitespace(self):
        assert normalize_arabic("خرسانة    مسلحة") == "خرسانه مسلحه"

    def test_handles_empty(self):
        assert normalize_arabic("") == ""
        assert normalize_arabic(None) == ""


class TestUnitNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("م3", "m3"),
            ("م³", "m3"),
            ("متر مكعب", "m3"),
            ("م2", "m2"),
            ("متر مربع", "m2"),
            ("طن", "ton"),
            ("عدد", "no"),
            ("نمرة", "no"),
            ("m3", "m3"),
        ],
    )
    def test_normalizes_units(self, raw, expected):
        assert normalize_unit(raw) == expected

    def test_units_compatible(self):
        assert units_compatible("م3", "m3")
        assert units_compatible("متر مكعب", "m3")
        assert not units_compatible("m3", "m2")
        assert not units_compatible("طن", "no")
