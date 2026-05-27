"""Win probability engine tests."""

import random
from uuid import uuid4

from api.services.win_probability import (
    CompetitorScenario,
    WinProbabilityEngine,
)


def _scenarios(n_comps: int, mid: float, spread: float = 0.05):
    return [
        CompetitorScenario(
            competitor_id=uuid4(),
            entry_probability=0.9,
            bid_low=mid * (1 - spread),
            bid_high=mid * (1 + spread),
        )
        for _ in range(n_comps)
    ]


def test_lower_bid_higher_win_probability():
    engine = WinProbabilityEngine()
    scenarios = _scenarios(3, mid=1000.0)
    rng = random.Random(42)

    low_bid = engine.calculate(900.0, scenarios, iterations=2000, rng=rng).probability
    rng = random.Random(42)
    high_bid = engine.calculate(1100.0, scenarios, iterations=2000, rng=rng).probability

    assert low_bid > high_bid


def test_no_competitors_returns_certain_win():
    engine = WinProbabilityEngine()
    result = engine.calculate(1000.0, [], iterations=100)
    assert result.probability == 1.0


def test_iterations_parameter_used():
    engine = WinProbabilityEngine()
    result = engine.calculate(900.0, _scenarios(2, 1000.0), iterations=500)
    assert result.iterations == 500


def test_optimal_bid_finds_best():
    engine = WinProbabilityEngine()
    scenarios = _scenarios(3, mid=1000.0, spread=0.10)
    result = engine.find_optimal_bid(
        scenarios=scenarios,
        reference_total=1000.0,
        estimated_cost=800.0,
        min_margin_pct=0.05,
        max_margin_pct=0.25,
        steps=21,
        rng=random.Random(123),
    )
    assert result.recommended_bid > 800.0
    assert 0.0 <= result.expected_win_probability <= 1.0
    assert result.expected_margin_pct >= 0.05
    assert len(result.sensitivity_curve) == 21


def test_probability_in_unit_range():
    engine = WinProbabilityEngine()
    result = engine.calculate(950.0, _scenarios(2, 1000.0), iterations=1000)
    assert 0.0 <= result.probability <= 1.0
    assert 0.0 <= result.confidence <= 1.0
