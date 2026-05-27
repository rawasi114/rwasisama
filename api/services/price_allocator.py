"""Reverse price-allocation service.

Implements spec section 7: given an awarded tender value V and a list of
BoQ items with quantities and (hopefully) historical reference prices,
infer per-item unit prices that:

1. Reproduce V exactly when multiplied back through quantities.
2. Reflect the empirical observation that winners discount unevenly:
   commodities take deeper cuts; specialties hold their margin.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from api.core.errors import AllocationError
from api.core.logging import get_logger
from api.utils.stats import clamp

LOG = get_logger(__name__)


COMMODITY_HINT_CATEGORIES = {"commodity", "materials"}
SPECIALTY_HINT_CATEGORIES = {"specialty", "labor_specialty"}


@dataclass
class AllocationInput:
    boq_item_id: UUID | None
    master_item_id: UUID | None
    quantity: float
    reference_price: float | None
    reference_confidence: float = 0.5
    category_hint: str | None = None
    historical_observations: int = 0


@dataclass
class AllocationResult:
    boq_item_id: UUID | None
    unit_price: float
    total_price: float
    confidence: float
    method: str


class PriceAllocator:
    """Distributes an award value across BoQ items using reference prices."""

    SUM_TOLERANCE = 1.0  # SAR

    def allocate(
        self,
        items: Sequence[AllocationInput],
        award_value: float,
        *,
        winner_pricing_pattern: dict[str, float] | None = None,
    ) -> list[AllocationResult]:
        if award_value <= 0:
            raise AllocationError("award_value must be positive")
        if not items:
            raise AllocationError("cannot allocate to empty item list")
        if any(it.quantity <= 0 for it in items):
            raise AllocationError("all quantities must be positive")

        # Step 1: market reference total (using fallback for missing refs)
        fallback_ref = _category_fallback_price(items)
        market_total = 0.0
        effective_refs: list[float] = []
        for it in items:
            ref = it.reference_price or fallback_ref
            if ref <= 0:
                ref = fallback_ref or 1.0
            effective_refs.append(ref)
            market_total += ref * it.quantity

        if market_total <= 0:
            return self._uniform_distribute(items, award_value)

        # Step 2: global discount factor
        d_global = award_value / market_total
        deviation = abs(1 - d_global)

        # Step 3: item weights (specialties resist discount, commodities take more)
        weights = self._compute_item_weights(
            items, effective_refs, market_total, winner_pricing_pattern
        )

        # Step 4: raw prices
        raw_unit_prices: list[float] = []
        for ref, w in zip(effective_refs, weights, strict=True):
            raw_unit_prices.append(ref * d_global * w)

        # Step 5: renormalize so the sum equals V exactly
        current_total = sum(p * it.quantity for p, it in zip(raw_unit_prices, items, strict=True))
        if current_total <= 0:
            return self._uniform_distribute(items, award_value)
        norm = award_value / current_total

        results: list[AllocationResult] = []
        for it, raw, _ref in zip(items, raw_unit_prices, effective_refs, strict=True):
            unit_price = raw * norm
            total_price = unit_price * it.quantity
            confidence = _inference_confidence(
                ref_confidence=it.reference_confidence,
                global_discount_severity=deviation,
                item_volume_share=total_price / award_value if award_value else 0,
                historical_data_count=it.historical_observations,
            )
            results.append(
                AllocationResult(
                    boq_item_id=it.boq_item_id,
                    unit_price=unit_price,
                    total_price=total_price,
                    confidence=confidence,
                    method="weighted_proportional",
                )
            )

        # Invariant check
        total_check = sum(r.total_price for r in results)
        if abs(total_check - award_value) > self.SUM_TOLERANCE:
            raise AllocationError(
                f"allocation invariant violated: sum={total_check:.2f} vs award={award_value:.2f}"
            )
        return results

    def _uniform_distribute(
        self, items: Sequence[AllocationInput], award_value: float
    ) -> list[AllocationResult]:
        per_item = award_value / sum(it.quantity for it in items)
        results: list[AllocationResult] = []
        for it in items:
            unit_price = per_item
            results.append(
                AllocationResult(
                    boq_item_id=it.boq_item_id,
                    unit_price=unit_price,
                    total_price=unit_price * it.quantity,
                    confidence=0.2,
                    method="uniform_fallback",
                )
            )
        return results

    def _compute_item_weights(
        self,
        items: Sequence[AllocationInput],
        refs: Sequence[float],
        market_total: float,
        winner_pricing_pattern: dict[str, float] | None,
    ) -> list[float]:
        weights: list[float] = []
        for it, ref in zip(items, refs, strict=True):
            w = 1.0
            volume_share = (ref * it.quantity) / market_total if market_total else 0.0
            if volume_share > 0.10:
                w *= 0.95
            elif volume_share < 0.01:
                w *= 1.05

            cat = (it.category_hint or "").lower()
            if cat in SPECIALTY_HINT_CATEGORIES:
                w *= 1.10
            elif cat in COMMODITY_HINT_CATEGORIES:
                w *= 0.93

            if winner_pricing_pattern and cat in winner_pricing_pattern:
                w *= winner_pricing_pattern[cat]

            weights.append(w)
        return weights


def _category_fallback_price(items: Sequence[AllocationInput]) -> float:
    """Median of known references, used to fill in missing ones."""
    known = [it.reference_price for it in items if it.reference_price]
    if not known:
        return 0.0
    s = sorted(known)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _inference_confidence(
    ref_confidence: float,
    global_discount_severity: float,
    item_volume_share: float,
    historical_data_count: int,
) -> float:
    base = clamp(ref_confidence, 0, 1) * 0.40
    discount_component = max(0.0, 0.20 - global_discount_severity * 0.5)
    volume_component = clamp(item_volume_share * 2, 0, 0.20)
    data_component = clamp(historical_data_count / 50 * 0.20, 0, 0.20)
    return clamp(base + discount_component + volume_component + data_component, 0.0, 1.0)
