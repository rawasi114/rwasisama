"""Anomaly detection edge cases."""

from datetime import date, timedelta

from api.models import Tender
from api.services.tender_service import TenderService


def _tender(seed, value: float, days_back: int) -> Tender:
    return Tender(
        title_ar="منافسة",
        government_entity_id=seed["entity"].id,
        region_id=seed["region"].id,
        primary_sector_id=seed["sector"].id,
        award_date=date.today() - timedelta(days=days_back),
        award_value=value,
        awarded_to_competitor_id=seed["competitor"].id,
    )


def test_no_anomaly_when_within_range(db, seed_entities):
    for i in range(6):
        db.add(_tender(seed_entities, 1_000_000 + i * 50_000, i * 30))
    db.commit()

    target = _tender(seed_entities, 1_100_000, 5)
    db.add(target)
    db.commit()

    service = TenderService(db)
    warning = service.check_anomaly(target)
    assert warning is None


def test_detects_anomaly(db, seed_entities):
    for i in range(8):
        db.add(_tender(seed_entities, 1_000_000, i * 30))
    db.commit()

    target = _tender(seed_entities, 10_000_000, 5)  # 10x the mean
    db.add(target)
    db.commit()

    service = TenderService(db)
    warning = service.check_anomaly(target)
    assert warning is not None
    assert "deviate" in warning.lower() or "انحراف" in warning
