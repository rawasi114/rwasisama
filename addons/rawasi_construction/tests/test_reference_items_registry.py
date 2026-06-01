# -*- coding: utf-8 -*-
"""اختبارات سجل البنود المرجعي ومنظومة المطابقة الذكية."""
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged("post_install", "-at_install")
class TestAutoNormalization(TransactionCase):
    """اختبار التوحيد التلقائي للوحدات والنصوص."""

    def test_unit_normalization_13_to_5(self):
        from odoo.addons.rawasi_construction.services.auto_normalization import (
            normalize_unit,
        )
        # 5 وحدات معتمدة
        cases = [
            ("م²", "SQM"), ("م2", "SQM"), ("متر مربع", "SQM"),
            ("م³", "CBM"), ("م3", "CBM"), ("م4", "CBM"),  # م4 خطأ مطبعي شائع
            ("م.ط", "MTR"), ("م ط", "MTR"), ("م/ط", "MTR"), ("متر", "MTR"),
            ("عدد", "EA"), ("وحدة", "EA"),
            ("كجم", "KG"),
        ]
        for raw, expected in cases:
            code, _ = normalize_unit(raw)
            self.assertEqual(code, expected, f"failed for {raw!r}")

    def test_unit_normalization_returns_none_for_unknown(self):
        from odoo.addons.rawasi_construction.services.auto_normalization import (
            normalize_unit,
        )
        code, _ = normalize_unit("xxx")
        self.assertIsNone(code)

    def test_text_normalization_strips_diacritics(self):
        from odoo.addons.rawasi_construction.services.auto_normalization import (
            normalize_text_full,
        )
        result = normalize_text_full("خَرَسانَةٌ مُسَلَّحَة")
        self.assertEqual(result, "خرسانه مسلحه")

    def test_text_normalization_arabic_digits(self):
        from odoo.addons.rawasi_construction.services.auto_normalization import (
            normalize_text_full,
        )
        self.assertEqual(normalize_text_full("قطعة ٢٥"), "قطعه 25")


@tagged("post_install", "-at_install")
class TestSpecificationsExtractor(TransactionCase):
    """اختبار مستخلص المواصفات بـ regex."""

    def test_extract_dimensions(self):
        from odoo.addons.rawasi_construction.services.specifications_extractor import (
            extract_dimensions,
        )
        self.assertEqual(extract_dimensions("بلاط 60×60"), "60x60")
        self.assertEqual(extract_dimensions("60x60"), "60x60")
        self.assertEqual(extract_dimensions("100*200*50"), "100x200x50")
        self.assertIsNone(extract_dimensions("no dimensions"))

    def test_extract_thickness(self):
        from odoo.addons.rawasi_construction.services.specifications_extractor import (
            extract_thickness,
        )
        self.assertEqual(extract_thickness("سمك 10 سم"), "10 سم")
        self.assertEqual(extract_thickness("سماكة (10)سم"), "10 سم")

    def test_extract_strength_c30(self):
        from odoo.addons.rawasi_construction.services.specifications_extractor import (
            extract_strength,
        )
        self.assertEqual(extract_strength("C30 concrete"), "30 N/mm²")
        self.assertEqual(extract_strength("جهد 25 نيوتن/مم2"), "25 N/mm²")


@tagged("post_install", "-at_install")
class TestHierarchyClassifier(TransactionCase):
    """اختبار مُصنِّف الهرمية الرباعية."""

    def test_concrete_reinforced(self):
        from odoo.addons.rawasi_construction.services.hierarchy_classifier import (
            classify,
        )
        result = classify("خرسانة مسلحة للقواعد جهد 35 نيوتن")
        self.assertEqual(result["main_category"], "الأعمال الإنشائية")
        self.assertEqual(result["item_group"], "الخرسانة المصبوبة بالموقع")
        self.assertEqual(result["simplified_desc"], "خرسانة مسلحة قواعد")

    def test_porcelain_tiles(self):
        from odoo.addons.rawasi_construction.services.hierarchy_classifier import (
            classify,
        )
        result = classify("بلاط بورسلين 60×60")
        self.assertEqual(result["main_category"], "أعمال التشطيبات والعزل")
        self.assertEqual(result["item_group"], "الأرضيات والجدران")
        self.assertEqual(result["simplified_desc"], "بلاط بورسلين")

    def test_excavation(self):
        from odoo.addons.rawasi_construction.services.hierarchy_classifier import (
            classify,
        )
        result = classify("اعمال الحفريات لزوم القواعد")
        self.assertEqual(result["main_category"], "الأعمال الإنشائية")

    def test_no_match_returns_nones(self):
        from odoo.addons.rawasi_construction.services.hierarchy_classifier import (
            classify,
        )
        result = classify("xyz unknown text")
        self.assertIsNone(result["main_category"])


@tagged("post_install", "-at_install")
class TestReferenceItem(TransactionCase):
    """اختبارات نموذج البند المرجعي."""

    def setUp(self):
        super().setUp()
        self.taxonomy_vals = {
            "main_category": "أعمال التشطيبات والعزل",
            "item_group": "الأرضيات والجدران",
            "simplified_desc": "بلاط بورسلين",
        }

    def test_create_reference_item(self):
        ref = self.env["rawasi.reference.item"].create({
            "reference_code": "FLR-POR-6060-001",
            "approved_name": "بلاط بورسلين 60×60",
            **self.taxonomy_vals,
        })
        self.assertEqual(ref.reference_code, "FLR-POR-6060-001")
        self.assertEqual(ref.variant_count, 0)

    def test_reference_code_format_validated(self):
        with self.assertRaises(ValidationError):
            self.env["rawasi.reference.item"].create({
                "reference_code": "BAD CODE",
                "approved_name": "بلاط",
                **self.taxonomy_vals,
            })

    def test_unique_reference_code(self):
        self.env["rawasi.reference.item"].create({
            "reference_code": "FLR-POR-6060-001",
            "approved_name": "بلاط أول",
            **self.taxonomy_vals,
        })
        from psycopg2 import IntegrityError
        from odoo.tools.misc import mute_logger
        with self.assertRaises(Exception):
            with mute_logger("odoo.sql_db"):
                self.env["rawasi.reference.item"].create({
                    "reference_code": "FLR-POR-6060-001",
                    "approved_name": "بلاط آخر",
                    **self.taxonomy_vals,
                })


@tagged("post_install", "-at_install")
class TestItemVariant(TransactionCase):
    """اختبارات الصياغة البديلة + التطبيع التلقائي للنص."""

    def setUp(self):
        super().setUp()
        self.ref = self.env["rawasi.reference.item"].create({
            "reference_code": "FLR-POR-6060-001",
            "approved_name": "بلاط بورسلين 60×60",
            "main_category": "أعمال التشطيبات والعزل",
            "item_group": "الأرضيات والجدران",
        })

    def test_variant_normalizes_text(self):
        v = self.env["rawasi.item.variant"].create({
            "reference_item_id": self.ref.id,
            "original_text": "بَلاطُ بُورْسِلين ٦٠×٦٠",
        })
        self.assertEqual(v.normalized_text, "بلاط بورسلين 60×60")


@tagged("post_install", "-at_install")
class TestImportBatchLinkedTender(TransactionCase):
    """اختبار الربط الإلزامي بالمنافسة."""

    def test_linked_tender_required(self):
        with self.assertRaises(Exception):
            self.env["rawasi.import.batch"].create({
                "filename": "test.xlsx",
                "file_data": b"YQ==",
                # linked_tender_id غير مُعطى → يفشل
            })

    def test_batch_with_tender_ok(self):
        tender = self.env["rawasi.competition"].create({"name": "م. اختبار"})
        batch = self.env["rawasi.import.batch"].create({
            "filename": "test.xlsx",
            "file_data": b"YQ==",
            "linked_tender_id": tender.id,
        })
        self.assertEqual(batch.linked_tender_id, tender)
        self.assertEqual(batch.state, "draft")


@tagged("post_install", "-at_install")
class TestMatchingEngine(TransactionCase):
    """اختبارات منظومة المطابقة الذكية."""

    def setUp(self):
        super().setUp()
        self.ref = self.env["rawasi.reference.item"].create({
            "reference_code": "FLR-POR-6060-001",
            "approved_name": "بلاط بورسلين 60×60",
            "main_category": "أعمال التشطيبات والعزل",
            "item_group": "الأرضيات والجدران",
        })
        self.env["rawasi.item.variant"].create({
            "reference_item_id": self.ref.id,
            "original_text": "بلاط بورسلين 60×60",
        })

    def test_level_1_exact_text_match(self):
        from odoo.addons.rawasi_construction.services.matching_engine import find_match
        ref, conf, src = find_match(self.env, "بلاط بورسلين 60×60")
        self.assertEqual(ref, self.ref)
        self.assertEqual(conf, 100.0)
        self.assertEqual(src, "exact_text")

    def test_no_match_returns_none(self):
        from odoo.addons.rawasi_construction.services.matching_engine import find_match
        ref, conf, src = find_match(self.env, "نص لا يطابق شيئاً")
        self.assertFalse(ref)
        self.assertEqual(conf, 0.0)
        self.assertEqual(src, "none")
