"""BoQ file import tests — cover all critical acceptance criteria."""

from __future__ import annotations

import io
from datetime import date
from uuid import uuid4

import pytest
from openpyxl import Workbook

from api.core.errors import NotFoundError, ValidationError
from api.models import RawasiBidItem, Tender, TenderBoqItem, TenderFile
from api.services.boq_importer import (
    BoqImporter,
)


def _build_tender(seed) -> Tender:
    return Tender(
        title_ar="منافسة اختبار جدول الكميات",
        government_entity_id=seed["entity"].id,
        region_id=seed["region"].id,
        primary_sector_id=seed["sector"].id,
        award_date=date(2026, 5, 15),
        award_value=1_500_000.00,
        awarded_to_competitor_id=seed["competitor"].id,
    )


def _build_excel(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "BoQ"
    ws.append(["م", "الوصف", "الوحدة", "الكمية", "سعر الوحدة", "الإجمالي"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def tender(db, seed_entities) -> Tender:
    t = _build_tender(seed_entities)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture
def importer(db, tmp_path) -> BoqImporter:
    return BoqImporter(db, uploads_root=tmp_path)


class TestExcelParsing:
    def test_upload_excel_extracts_items_correctly(self, db, tender, importer):
        file_bytes = _build_excel(
            [
                ["1.1", "خرسانة مسلحة 30 ميجا", "m3", 100, 500.0, 50000.0],
                ["1.2", "حديد تسليح قطر 12 مم", "ton", 8, 3000.0, 24000.0],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            boq_type="original_tender",
        )
        assert preview.total_items == 2
        assert preview.parser == "excel"
        assert preview.items[0].description == "خرسانة مسلحة 30 ميجا"
        assert preview.items[0].quantity == 100
        assert preview.items[1].unit == "ton"

    def test_excel_with_arabic_unit_codes(self, db, tender, importer):
        file_bytes = _build_excel(
            [
                ["1", "دهان داخلي", "م2", 250, None, None],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        assert preview.total_items == 1
        assert preview.items[0].unit == "م2"

    def test_excel_skips_rows_without_quantity(self, db, tender, importer):
        file_bytes = _build_excel(
            [
                ["1", "بند صالح", "no", 10, None, None],
                ["", "", "", "", "", ""],
                ["2", "بند بدون كمية", "no", None, None, None],
                ["3", "بند صالح آخر", "no", 5, None, None],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        assert preview.total_items == 2


class TestCsvParsing:
    def test_csv_parses_utf8_with_bom(self, db, tender, importer):
        csv_content = (
            "﻿sequence,description,unit,quantity\n"
            "1.1,خرسانة 30 ميجا,m3,100\n"
            "1.2,حديد قطر 12,ton,8\n"
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=csv_content.encode("utf-8-sig"),
            filename="boq.csv",
            mime_type="text/csv",
            boq_type="original_tender",
        )
        assert preview.total_items == 2
        assert preview.parser == "csv"


class TestValidation:
    def test_boq_type_field_is_required_via_enum(self, db, tender, importer):
        with pytest.raises(ValidationError, match="boq_type must be one of"):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=_build_excel([["1", "x", "no", 1, None, None]]),
                filename="boq.xlsx",
                mime_type=None,
                boq_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_unsupported_file_format_returns_clear_arabic_error(
        self, db, tender, importer
    ):
        with pytest.raises(ValidationError, match="صيغة الملف غير مدعومة"):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=b"fake pptx content",
                filename="presentation.pptx",
                mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                boq_type="original_tender",
            )

    def test_oversized_file_rejected_before_processing(self, db, tender, importer):
        huge_file = b"x" * (11 * 1024 * 1024)  # 11 MB > 10 MB limit
        with pytest.raises(ValidationError, match="يتجاوز الحد الأقصى"):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=huge_file,
                filename="boq.xlsx",
                mime_type=None,
                boq_type="original_tender",
            )

    def test_empty_file_rejected(self, db, tender, importer):
        with pytest.raises(ValidationError, match="فارغ"):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=b"",
                filename="boq.xlsx",
                mime_type=None,
                boq_type="original_tender",
            )

    def test_unknown_tender_raises_not_found(self, db, importer):
        with pytest.raises(NotFoundError):
            importer.import_file(
                tender_id=uuid4(),
                file_bytes=_build_excel([["1", "x", "no", 1, None, None]]),
                filename="boq.xlsx",
                mime_type=None,
                boq_type="original_tender",
            )

    def test_competitor_boq_requires_competitor_id(self, db, tender, importer):
        with pytest.raises(ValidationError, match="source_competitor_id"):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=_build_excel([["1", "x", "no", 1, None, None]]),
                filename="boq.xlsx",
                mime_type=None,
                boq_type="competitor",
            )

    def test_non_competitor_boq_rejects_competitor_id(self, db, tender, importer):
        with pytest.raises(
            ValidationError, match="only valid when boq_type=competitor"
        ):
            importer.import_file(
                tender_id=tender.id,
                file_bytes=_build_excel([["1", "x", "no", 1, None, None]]),
                filename="boq.xlsx",
                mime_type=None,
                boq_type="original_tender",
                source_competitor_id=uuid4(),
            )


class TestFileStorage:
    def test_original_file_persisted_to_tender_files_table(
        self, db, tender, importer, tmp_path
    ):
        file_bytes = _build_excel(
            [["1.1", "خرسانة 30 ميجا", "m3", 100, None, None]]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="my_boq_file.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        # Verify TenderFile record was created
        files = db.query(TenderFile).filter_by(tender_id=tender.id).all()
        assert len(files) == 1
        assert files[0].id == preview.source_file_id
        assert files[0].filename == "my_boq_file.xlsx"
        assert files[0].file_type == "boq_original_tender"
        assert files[0].size_bytes == len(file_bytes)
        # And the file is on disk
        full_path = tmp_path / files[0].storage_path
        assert full_path.exists()
        assert full_path.read_bytes() == file_bytes


class TestConfirmAndCommit:
    def test_items_link_to_correct_tender_id_after_confirm(
        self, db, tender, importer
    ):
        file_bytes = _build_excel(
            [
                ["1.1", "خرسانة 30 ميجا", "m3", 100, 500.0, 50000.0],
                ["1.2", "حديد قطر 12", "ton", 8, 3000.0, 24000.0],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        committed = importer.confirm(
            tender_id=tender.id,
            boq_type="original_tender",
            items=preview.items,
            source_file_id=preview.source_file_id,
        )
        assert committed == 2
        rows = db.query(TenderBoqItem).filter_by(tender_id=tender.id).all()
        assert len(rows) == 2
        assert all(row.tender_id == tender.id for row in rows)
        assert all(row.boq_type == "original_tender" for row in rows)
        assert all(row.source_file_id == preview.source_file_id for row in rows)

    def test_confirm_sets_has_full_boq_on_tender(self, db, tender, importer):
        file_bytes = _build_excel([["1", "بند", "no", 1, None, None]])
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        importer.confirm(
            tender_id=tender.id,
            boq_type="original_tender",
            items=preview.items,
            source_file_id=preview.source_file_id,
        )
        db.refresh(tender)
        assert tender.has_full_boq is True

    def test_rawasi_boq_writes_to_rawasi_bid_items_table(
        self, db, tender, importer
    ):
        file_bytes = _build_excel(
            [
                ["1.1", "خرسانة 30 ميجا", "m3", 100, 510.0, 51000.0],
                ["1.2", "حديد قطر 12", "ton", 8, 2900.0, 23200.0],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="rawasi_boq.xlsx",
            mime_type=None,
            boq_type="rawasi",
        )
        importer.confirm(
            tender_id=tender.id,
            boq_type="rawasi",
            items=preview.items,
        )
        rows = db.query(RawasiBidItem).all()
        assert len(rows) == 2
        # Tender-level state should reflect rawasi participation
        db.refresh(tender)
        assert tender.rawasi_participated is True
        assert tender.rawasi_bid_id is not None

    def test_competitor_boq_with_competitor_id(
        self, db, tender, importer, seed_entities
    ):
        file_bytes = _build_excel([["1", "بند", "no", 1, None, None]])
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="competitor_boq.xlsx",
            mime_type=None,
            boq_type="competitor",
            source_competitor_id=seed_entities["competitor"].id,
        )
        importer.confirm(
            tender_id=tender.id,
            boq_type="competitor",
            items=preview.items,
            source_file_id=preview.source_file_id,
            source_competitor_id=seed_entities["competitor"].id,
        )
        rows = db.query(TenderBoqItem).filter_by(tender_id=tender.id).all()
        assert all(row.boq_type == "competitor" for row in rows)
        assert all(
            row.source_competitor_id == seed_entities["competitor"].id for row in rows
        )


class TestNormalizationIntegration:
    def test_normalization_engine_triggered_during_import(
        self, db, tender, importer, seed_master_items
    ):
        from api.models import MasterItemSynonym

        target = seed_master_items["CONC-RC-30"]
        db.add(
            MasterItemSynonym(
                master_item_id=target.id,
                synonym_text="خرسانه مسلحه 30 ميجا",
                source="bootstrap",
            )
        )
        db.commit()

        file_bytes = _build_excel(
            [
                ["1.1", "خرسانة مسلحة 30 ميجا", "m3", 100, None, None],
                ["1.2", "بند غير معروف تماماً xyz", "no", 1, None, None],
            ]
        )
        preview = importer.import_file(
            tender_id=tender.id,
            file_bytes=file_bytes,
            filename="boq.xlsx",
            mime_type=None,
            boq_type="original_tender",
        )
        # The seeded synonym should match the first item
        assert preview.items[0].master_item_code == "CONC-RC-30"
        # The unknown item should be flagged for manual review
        assert preview.items[1].requires_manual_review is True
        assert preview.items_needing_review >= 1


class TestApiEndpoint:
    def test_upload_endpoint_via_fastapi(self, db, tender, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from api.main import app
        from api.routers import boq_import as boq_router

        # Force the router to use our tmp uploads dir
        def _factory(db):
            return BoqImporter(db, uploads_root=tmp_path)

        monkeypatch.setattr(boq_router, "_make_importer", _factory)

        file_bytes = _build_excel(
            [["1.1", "خرسانة 30 ميجا", "m3", 100, None, None]]
        )
        client = TestClient(app)
        response = client.post(
            f"/tenders/{tender.id}/boq/upload",
            files={
                "file": (
                    "boq.xlsx",
                    file_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"boq_type": "original_tender"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total_items"] == 1
        assert body["boq_type"] == "original_tender"
        assert len(body["items"]) == 1

    def test_upload_endpoint_rejects_invalid_boq_type(self, db, tender):
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        response = client.post(
            f"/tenders/{tender.id}/boq/upload",
            files={"file": ("boq.xlsx", b"x", "text/plain")},
            data={"boq_type": "not_a_real_type"},
        )
        assert response.status_code == 422  # Pydantic enum validation
