"""End-to-end workflow test exercising the full pricing intelligence pipeline.

Scenario: a new tender lands, gets normalized, allocated, and analyzed.
"""

from uuid import uuid4

from api.services.boq_normalizer import BoqNormalizer
from api.services.go_no_go import GoNoGoEngine, GoNoGoInput
from api.services.price_allocator import AllocationInput, PriceAllocator
from api.services.win_probability import (
    CompetitorScenario,
    WinProbabilityEngine,
)


def test_complete_workflow(db, seed_entities, seed_master_items):
    """Smoke test that proves all engines wire together."""
    from api.models import MasterItemSynonym

    # 1. Seed synonyms so normalization can find matches
    for code, text in [
        ("CONC-RC-30", "خرسانه مسلحه بمقاومه 30 ميجا"),
        ("STEEL-REBAR-Y12", "حديد تسليح قطر 12 مم درجه 60"),
        ("PAINT-INT-PLST", "دهان بلاستيكي داخلي درجه اولي"),
    ]:
        db.add(
            MasterItemSynonym(
                master_item_id=seed_master_items[code].id,
                synonym_text=text,
                source="bootstrap",
            )
        )
    db.commit()

    # 2. Simulate a new tender's BoQ
    raw_items = [
        ("خرسانة مسلحة بمقاومة 30 ميجا", "m3", 100, "civil"),
        ("حديد تسليح قطر 12 مم درجة 60", "ton", 8, "civil"),
        ("دهان بلاستيكي داخلي درجة أولى", "m2", 5000, "finishing"),
    ]

    # 3. Normalize each item
    normalizer = BoqNormalizer(db)
    normalized_items = []
    for desc, unit, qty, cat in raw_items:
        outcome = normalizer.normalize(desc, unit, use_claude=False)
        assert outcome.match_found, f"Failed to normalize: {desc}"
        normalized_items.append((outcome.master_item_id, qty, cat))

    # 4. Allocate prices given an award value
    allocator = PriceAllocator()
    allocation_inputs = [
        AllocationInput(
            boq_item_id=uuid4(),
            master_item_id=mid,
            quantity=qty,
            reference_price=500.0 if "خرسانة" in raw_items[i][0]
            else 3000.0 if "حديد" in raw_items[i][0]
            else 25.0,
            reference_confidence=0.7,
            category_hint=cat,
        )
        for i, (mid, qty, cat) in enumerate(normalized_items)
    ]
    award_value = 200_000.00
    results = allocator.allocate(allocation_inputs, award_value)
    total = sum(r.total_price for r in results)
    assert abs(total - award_value) < 1.0, f"Allocation invariant violated: {total} vs {award_value}"

    # 5. Win probability simulation
    win_engine = WinProbabilityEngine()
    scenarios = [
        CompetitorScenario(
            competitor_id=uuid4(),
            entry_probability=0.7,
            bid_low=190_000,
            bid_high=210_000,
        )
        for _ in range(3)
    ]
    win_result = win_engine.calculate(
        proposed_bid=195_000, scenarios=scenarios, iterations=500
    )
    assert 0 <= win_result.probability <= 1

    # 6. Go/No-Go evaluation
    go_engine = GoNoGoEngine()
    decision = go_engine.evaluate(
        GoNoGoInput(
            estimated_award_value=award_value,
            expected_competitors=3,
            expected_margin_pct=8.0,
            rawasi_capacity_load_pct=50.0,
            relationship_with_entity="good",
            sector_strategic_priority="high",
            payment_terms_score=0.8,
            item_overlap_with_capacity_pct=0.9,
        ),
        win_probability=win_result.probability,
    )
    assert decision.recommendation in {"GO", "REVIEW", "NO_GO"}
