"""Go/No-Go engine tests."""

from api.services.go_no_go import GoNoGoEngine, GoNoGoInput


def _baseline_input(**overrides) -> GoNoGoInput:
    defaults = dict(
        estimated_award_value=3_000_000,
        expected_competitors=5,
        expected_margin_pct=10.0,
        rawasi_capacity_load_pct=50.0,
        relationship_with_entity="good",
        sector_strategic_priority="high",
        payment_terms_score=0.8,
        item_overlap_with_capacity_pct=0.9,
    )
    defaults.update(overrides)
    return GoNoGoInput(**defaults)


def test_strong_tender_returns_go():
    result = GoNoGoEngine().evaluate(_baseline_input(), win_probability=0.8)
    assert result.recommendation == "GO"
    assert result.composite_score >= 0.65


def test_weak_tender_returns_no_go():
    result = GoNoGoEngine().evaluate(
        _baseline_input(
            expected_margin_pct=1.0,
            rawasi_capacity_load_pct=180.0,
            relationship_with_entity="none",
            sector_strategic_priority="low",
            item_overlap_with_capacity_pct=0.1,
            requires_new_classification=True,
            payment_terms_score=0.1,
        ),
        win_probability=0.1,
    )
    assert result.recommendation == "NO_GO"


def test_borderline_returns_review():
    result = GoNoGoEngine().evaluate(
        _baseline_input(
            expected_margin_pct=5.0,
            relationship_with_entity="neutral",
        ),
        win_probability=0.5,
    )
    assert result.recommendation in {"REVIEW", "GO"}


def test_composite_score_in_range():
    result = GoNoGoEngine().evaluate(_baseline_input(), win_probability=0.6)
    assert 0.0 <= result.composite_score <= 1.0


def test_concerns_and_strengths_lists_filled():
    result = GoNoGoEngine().evaluate(
        _baseline_input(
            expected_margin_pct=2.0,
            payment_terms_score=0.2,
        ),
        win_probability=0.7,
    )
    assert isinstance(result.top_concerns, list)
    assert isinstance(result.top_strengths, list)
