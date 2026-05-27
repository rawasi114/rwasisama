"""Integration tests for the Tender CRUD service."""

from datetime import date

import pytest

from api.core.errors import NotFoundError, ValidationError
from api.schemas.tender import BoqItemIn, TenderBidderIn, TenderCreate, TenderUpdate
from api.services.tender_service import TenderService


def _make_tender_create(seed, **overrides) -> TenderCreate:
    defaults = dict(
        etimad_tender_id="40-2026م",
        title_ar="توريد أثاث مكتبي للمبنى الجديد",
        government_entity_id=seed["entity"].id,
        region_id=seed["region"].id,
        primary_sector_id=seed["sector"].id,
        award_date=date(2026, 5, 15),
        award_value=2_847_500.00,
        awarded_to_competitor_id=seed["competitor"].id,
        rawasi_participated=False,
        total_bidders_count=7,
    )
    defaults.update(overrides)
    return TenderCreate(**defaults)


def test_create_basic_tender(db, seed_entities):
    service = TenderService(db)
    tender = service.create(_make_tender_create(seed_entities))
    assert tender.id is not None
    assert tender.etimad_tender_id == "40-2026م"
    assert float(tender.award_value) == 2_847_500.00


def test_create_with_boq_items(db, seed_entities):
    service = TenderService(db)
    data = _make_tender_create(
        seed_entities,
        boq_items=[
            BoqItemIn(
                sequence_number="1.1",
                original_description="مكتب تنفيذي",
                original_unit="no",
                quantity=10,
            ),
            BoqItemIn(
                sequence_number="1.2",
                original_description="كرسي تنفيذي",
                original_unit="no",
                quantity=10,
            ),
        ],
    )
    tender = service.create(data)
    assert tender.has_full_boq is True
    assert len(tender.boq_items) == 2


def test_create_with_bidders(db, seed_entities):
    service = TenderService(db)
    data = _make_tender_create(
        seed_entities,
        rawasi_participated=True,
        total_bidders_count=3,
        bidders=[
            TenderBidderIn(
                bidder_name_as_appeared="شركة الديار للأثاث",
                bid_rank=1,
                bid_amount=2_847_500,
            ),
            TenderBidderIn(
                bidder_name_as_appeared="شركة رواسي سما",
                bid_rank=2,
                bid_amount=2_950_000,
            ),
        ],
    )
    tender = service.create(data)
    assert len(tender.bidders) == 2


def test_rejects_duplicate_etimad_id(db, seed_entities):
    service = TenderService(db)
    service.create(_make_tender_create(seed_entities))
    with pytest.raises(ValidationError):
        service.create(_make_tender_create(seed_entities))


def test_rejects_invalid_dates(db, seed_entities):
    service = TenderService(db)
    with pytest.raises(ValidationError):
        service.create(
            _make_tender_create(
                seed_entities,
                publication_date=date(2026, 6, 1),
                award_date=date(2026, 5, 15),  # before publication
            )
        )


def test_rejects_invalid_entity(db, seed_entities):
    from uuid import uuid4

    service = TenderService(db)
    with pytest.raises(ValidationError):
        service.create(
            _make_tender_create(
                seed_entities,
                government_entity_id=uuid4(),
            )
        )


def test_update_tender(db, seed_entities):
    service = TenderService(db)
    tender = service.create(_make_tender_create(seed_entities))
    updated = service.update(tender.id, TenderUpdate(notes="ملاحظة محدّثة"))
    assert updated.notes == "ملاحظة محدّثة"


def test_get_missing_tender_raises(db):
    from uuid import uuid4

    service = TenderService(db)
    with pytest.raises(NotFoundError):
        service.get(uuid4())


def test_list_with_filters(db, seed_entities):
    service = TenderService(db)
    service.create(_make_tender_create(seed_entities))
    results = service.list(government_entity_id=seed_entities["entity"].id)
    assert len(results) == 1


def test_anomaly_check_with_no_peers_returns_none(db, seed_entities):
    service = TenderService(db)
    tender = service.create(_make_tender_create(seed_entities))
    warning = service.check_anomaly(tender)
    assert warning is None  # not enough peers
