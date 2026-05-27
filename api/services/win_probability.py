"""Win-probability engine — engine #4 (Monte Carlo)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from api.core.config import Settings, get_settings
from api.schemas.analytics import OptimalBidResult, WinProbabilityResult
from api.utils.stats import clamp


@dataclass
class CompetitorScenario:
    competitor_id: UUID
    entry_probability: float
    bid_low: float
    bid_high: float


class WinProbabilityEngine:
    """Engine #4: Monte-Carlo simulation of bid outcomes."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def calculate(
        self,
        proposed_bid: float,
        scenarios: Sequence[CompetitorScenario],
        *,
        technical_advantage: float = 0.0,
        iterations: int | None = None,
        rng: random.Random | None = None,
    ) -> WinProbabilityResult:
        """Compute the win probability assuming a price+technical evaluation.

        ``technical_advantage`` is on a -1..1 scale (Rawasi-vs-baseline)
        and shifts the combined score (40% tech / 60% financial).
        """
        if proposed_bid <= 0:
            raise ValueError("proposed_bid must be > 0")

        random_gen = rng or random.Random()
        n = iterations or self.settings.win_probability_iterations

        wins = 0
        runs_with_competition = 0

        for _ in range(n):
            competitor_bids: list[float] = []
            for scn in scenarios:
                if random_gen.random() < clamp(scn.entry_probability, 0.0, 1.0):
                    bid = random_gen.uniform(scn.bid_low, scn.bid_high)
                    competitor_bids.append(bid)
            if not competitor_bids:
                wins += 1
                continue

            runs_with_competition += 1
            lowest_comp = min(competitor_bids)
            rawasi_score = self._combined_score(proposed_bid, technical_advantage)
            comp_score = self._combined_score(lowest_comp, 0.0)
            if rawasi_score > comp_score:
                wins += 1

        probability = wins / n
        confidence = clamp(0.5 + 0.5 * (runs_with_competition / n), 0.4, 0.95)
        return WinProbabilityResult(
            probability=probability,
            confidence=confidence,
            expected_competitors=[s.competitor_id for s in scenarios],
            sensitivity_analysis=[],
            iterations=n,
            runs_with_competition=runs_with_competition,
        )

    def find_optimal_bid(
        self,
        scenarios: Sequence[CompetitorScenario],
        reference_total: float,
        estimated_cost: float,
        *,
        min_margin_pct: float = 0.03,
        max_margin_pct: float = 0.25,
        steps: int = 41,
        technical_advantage: float = 0.0,
        rng: random.Random | None = None,
    ) -> OptimalBidResult:
        if reference_total <= 0:
            raise ValueError("reference_total must be > 0")
        if estimated_cost <= 0:
            raise ValueError("estimated_cost must be > 0")

        low = max(estimated_cost * (1 + min_margin_pct), reference_total * 0.70)
        high = max(low + 1, min(reference_total * 1.10, estimated_cost * (1 + max_margin_pct)))
        if steps < 2:
            steps = 2
        step_size = (high - low) / (steps - 1)

        curve: list[dict] = []
        best: dict | None = None
        for i in range(steps):
            bid = low + i * step_size
            margin = (bid - estimated_cost) / bid
            win_p = self.calculate(
                bid, scenarios, technical_advantage=technical_advantage, rng=rng
            ).probability
            expected = win_p * margin * bid
            row = {
                "bid_amount": bid,
                "margin_pct": margin,
                "win_probability": win_p,
                "expected_value": expected,
            }
            curve.append(row)
            if best is None or expected > best["expected_value"]:
                best = row

        assert best is not None
        return OptimalBidResult(
            recommended_bid=best["bid_amount"],
            expected_win_probability=best["win_probability"],
            expected_margin_pct=best["margin_pct"],
            sensitivity_curve=curve,
        )

    @staticmethod
    def _combined_score(bid: float, technical_advantage: float) -> float:
        """Lower bid → higher financial score; technical_advantage in [-1, 1]."""
        financial = 1.0 / max(bid, 1.0)
        return 0.6 * financial + 0.4 * (0.5 + 0.5 * clamp(technical_advantage, -1, 1))
