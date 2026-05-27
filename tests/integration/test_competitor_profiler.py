"""Competitor profile engine tests."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from api.core.errors import InsufficientDataError, NotFoundError
from api.models import Tender, TenderBidder
from api.services.competitor_profiler import CompetitorProfileEngine


def _add_history_for_competitor(db, seed, n_appearances: int, n_wins: int):
    competitor_id = seed["competitor"].id
    for i in range(n_appearances):
        tender = Tender(
            title_ar=f"منافسة {i}",
            government_entity_id=seed["entity"].id,
            region_id=seed["region"].id,
            primary_sector_id=seed["sector"].id,
            award_date=date.today() - timedelta(days=i * 30 + 10),
            award_value=1_000_000 + i * 100_000,
            awarded_to_competitor_id=seed["competitor"].id if i < n_wins else _make_other(db),
        )
        db.add(tender)
        db.flush()
        db.add(
            TenderBidder(
                tender_id=tender.id,
                competitor_id=competitor_id,
                bidder_name_as_appeared=seed["competitor"].name_ar,
                bid_rank=1 if i < n_wins else 2,
            )
        )
    db.commit()


def _make_other(db):
    from api.models import Competitor

    other = Competitor(name_ar=f"منافس آخر {uuid4().hex[:6]}")
    db.add(other)
    db.flush()
    return other.id


def test_build_profile_requires_data(db, seed_entities):
    engine = CompetitorProfileEngine(db)
    with pytest.raises(InsufficientDataError):
        engine.build_profile(seed_entities["competitor"].id)


def test_build_profile_with_history(db, seed_entities):
    _add_history_for_competitor(db, seed_entities, n_appearances=5, n_wins=2)
    engine = CompetitorProfileEngine(db)
    profile = engine.build_profile(seed_entities["competitor"].id)
    assert profile.total_appearances == 5
    assert profile.total_wins == 2
    assert profile.win_rate == pytest.approx(0.4, rel=0.01)
    assert profile.threat_score is not None
    assert 1 <= profile.threat_score <= 100


def test_unknown_competitor_raises(db):
    engine = CompetitorProfileEngine(db)
    with pytest.raises(NotFoundError):
        engine.build_profile(uuid4())


def test_profile_persisted(db, seed_entities):
    _add_history_for_competitor(db, seed_entities, n_appearances=4, n_wins=1)
    engine = CompetitorProfileEngine(db)
    engine.build_profile(seed_entities["competitor"].id)

    retrieved = engine.get_persisted_profile(seed_entities["competitor"].id)
    assert retrieved is not None
    assert retrieved.total_appearances == 4


def test_predict_bid_returns_default_when_no_profile(db, seed_entities):
    engine = CompetitorProfileEngine(db)
    tender = Tender(
        title_ar="منافسة جديدة",
        government_entity_id=seed_entities["entity"].id,
        region_id=seed_entities["region"].id,
        primary_sector_id=seed_entities["sector"].id,
        award_date=date.today(),
        award_value=1_000_000,
        awarded_to_competitor_id=seed_entities["competitor"].id,
    )
    db.add(tender)
    db.flush()

    pred = engine.predict_bid(
        seed_entities["competitor"].id, tender, reference_value=1_000_000
    )
    assert 0 <= pred.entry_probability <= 1
