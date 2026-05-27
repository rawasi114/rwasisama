"""Reference pricing engine tests."""

from datetime import date, timedelta

from api.models import Tender, TenderBoqItem
from api.services.reference_pricer import ContextFilters, ReferencePricingEngine


def _make_tender(seed, award_value: float, days_ago: int):
    return Tender(
        title_ar=f"منافسة قبل {days_ago} يوم",
        government_entity_id=seed["entity"].id,
        region_id=seed["region"].id,
        primary_sector_id=seed["sector"].id,
        award_date=date.today() - timedelta(days=days_ago),
        award_value=award_value,
        awarded_to_competitor_id=seed["competitor"].id,
    )


def _add_history(
    db, seed, master_item_id, prices, days_ago_per_price=30
):
    for i, price in enumerate(prices):
        tender = _make_tender(seed, price * 10, i * days_ago_per_price + 30)
        db.add(tender)
        db.flush()
        db.add(
            TenderBoqItem(
                tender_id=tender.id,
                original_description="x",
                quantity=10,
                master_item_id=master_item_id,
                inferred_unit_price=price,
                inference_confidence=0.8,
            )
        )
    db.commit()


def test_insufficient_data_returns_unavailable(db, seed_entities, seed_master_items):
    engine = ReferencePricingEngine(db)
    result = engine.get_reference_price(seed_master_items["CONC-RC-30"].id)
    assert result.available is False
    assert result.reason == "insufficient_data"


def test_with_enough_observations(db, seed_entities, seed_master_items):
    _add_history(db, seed_entities, seed_master_items["CONC-RC-30"].id, [100, 105, 110, 95, 102])

    engine = ReferencePricingEngine(db)
    result = engine.get_reference_price(seed_master_items["CONC-RC-30"].id)
    assert result.available is True
    assert 95 <= (result.weighted_mean or 0) <= 110
    assert result.observation_count == 5
    assert (result.p75 or 0) >= (result.p25 or 0)


def test_context_filter_narrows_observations(db, seed_entities, seed_master_items):
    _add_history(db, seed_entities, seed_master_items["CONC-RC-30"].id, [100, 105, 110, 95, 102])

    engine = ReferencePricingEngine(db)
    # Use a context that matches the seeded entity
    ctx = ContextFilters(
        government_entity_id=seed_entities["entity"].id,
        min_observations=3,
    )
    result = engine.get_reference_price(seed_master_items["CONC-RC-30"].id, ctx)
    assert result.available is True


def test_missing_master_item_returns_unavailable(db):
    engine = ReferencePricingEngine(db)
    result = engine.get_reference_price(None)
    assert result.available is False
    assert result.reason == "no_master_item"


def test_recommended_price_is_competitive(db, seed_entities, seed_master_items):
    _add_history(db, seed_entities, seed_master_items["CONC-RC-30"].id, [100, 110, 120, 130, 140])

    engine = ReferencePricingEngine(db)
    result = engine.get_reference_price(seed_master_items["CONC-RC-30"].id)
    # Recommended should be at or below the median
    assert result.recommended_for_rawasi is not None
    assert result.recommended_for_rawasi <= (result.weighted_median or float("inf"))
