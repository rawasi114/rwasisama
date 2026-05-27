"""Reference pricing engine — engine #1 of the four analytics engines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from api.core.config import Settings, get_settings
from api.models import Tender, TenderBoqItem
from api.schemas.analytics import (
    BoqPricingResult,
    PricedItemOut,
    ReferencePriceResult,
)
from api.services.boq_normalizer import BoqNormalizer
from api.utils.stats import (
    weighted_mean,
    weighted_median,
    weighted_percentile,
    weighted_std,
)


@dataclass
class ContextFilters:
    sector_id: UUID | None = None
    region_id: UUID | None = None
    government_entity_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_observations: int = 3

    def relaxed(self) -> ContextFilters:
        """Drop optional filters one step at a time for fallback queries."""
        return ContextFilters(
            sector_id=None,
            region_id=None,
            government_entity_id=None,
            date_from=self.date_from,
            date_to=self.date_to,
            min_observations=self.min_observations,
        )

    @classmethod
    def from_tender(cls, tender: Tender, lookback_months: int) -> ContextFilters:
        return cls(
            sector_id=tender.primary_sector_id,
            region_id=tender.region_id,
            government_entity_id=tender.government_entity_id,
            date_from=tender.award_date - timedelta(days=lookback_months * 30),
            date_to=tender.award_date,
        )


class ReferencePricingEngine:
    """Engine #1: weighted distribution of past unit prices for an item."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def get_reference_price(
        self,
        master_item_id: UUID | None,
        context: ContextFilters | None = None,
    ) -> ReferencePriceResult:
        if master_item_id is None:
            return ReferencePriceResult(available=False, reason="no_master_item")

        ctx = context or ContextFilters(
            min_observations=self.settings.reference_min_observations,
        )
        observations = self._gather_observations(master_item_id, ctx)
        if len(observations) < ctx.min_observations:
            observations = self._gather_observations(master_item_id, ctx.relaxed())

        if len(observations) < ctx.min_observations:
            return ReferencePriceResult(
                master_item_id=master_item_id,
                available=False,
                reason="insufficient_data",
                observation_count=len(observations),
                context_used=_ctx_to_dict(ctx),
            )

        prices = [float(p) for p, _ in observations]
        weights = [float(w) for _, w in observations]

        mean = weighted_mean(prices, weights)
        median = weighted_median(prices, weights)
        return ReferencePriceResult(
            master_item_id=master_item_id,
            available=True,
            weighted_mean=mean,
            weighted_median=median,
            p25=weighted_percentile(prices, weights, 25),
            p75=weighted_percentile(prices, weights, 75),
            min_value=min(prices),
            max_value=max(prices),
            std_deviation=weighted_std(prices, weights),
            observation_count=len(observations),
            recommended_for_rawasi=self._calculate_recommended(prices, weights, mean, median),
            context_used=_ctx_to_dict(ctx),
        )

    def price_full_boq(
        self,
        items: list,
        tender_context: ContextFilters | None = None,
        *,
        normalizer: BoqNormalizer | None = None,
    ) -> BoqPricingResult:
        priced: list[PricedItemOut] = []
        total_recommended = 0.0
        covered_value = 0.0
        total_value = 0.0
        confidences: list[float] = []

        for raw in items:
            description = getattr(raw, "original_description", None) or raw["description"]
            unit = getattr(raw, "original_unit", None) or raw.get("unit") if isinstance(raw, dict) else getattr(raw, "original_unit", None)
            quantity = getattr(raw, "quantity", None) or raw["quantity"]
            sequence = getattr(raw, "sequence_number", None) if not isinstance(raw, dict) else raw.get("sequence_number")
            master_item_id = getattr(raw, "master_item_id", None) if not isinstance(raw, dict) else raw.get("master_item_id")
            boq_item_id = getattr(raw, "id", None) if not isinstance(raw, dict) else raw.get("id")

            if master_item_id is None and normalizer is not None:
                outcome = normalizer.normalize(description, unit, use_claude=False)
                if outcome.match_found:
                    master_item_id = outcome.master_item_id

            ref = self.get_reference_price(master_item_id, tender_context)
            suggested = ref.recommended_for_rawasi if ref.available else None
            price_range = (
                (ref.p25 or 0.0, ref.p75 or 0.0) if ref.available and ref.p25 and ref.p75 else None
            )
            suggested_total = suggested * quantity if suggested else None

            if suggested_total is not None:
                covered_value += suggested_total
                total_recommended += suggested_total
            if ref.available:
                confidences.append(0.7)
            else:
                confidences.append(0.2)

            total_value += (suggested or ref.weighted_mean or 0.0) * quantity

            priced.append(
                PricedItemOut(
                    boq_item_id=boq_item_id,
                    sequence_number=sequence,
                    description=description,
                    unit=unit,
                    quantity=quantity,
                    master_item_id=master_item_id,
                    reference=ref,
                    suggested_unit_price=suggested,
                    unit_price_range=price_range,
                    suggested_total=suggested_total,
                )
            )

        coverage = (covered_value / total_value) if total_value > 0 else 0.0
        overall = sum(confidences) / len(confidences) if confidences else 0.0
        return BoqPricingResult(
            items=priced,
            total_recommended_value=total_recommended,
            coverage_pct=coverage,
            overall_confidence=overall,
        )

    def _gather_observations(
        self, master_item_id: UUID, ctx: ContextFilters
    ) -> list[tuple[float, float]]:
        stmt = (
            select(
                TenderBoqItem.inferred_unit_price,
                TenderBoqItem.inference_confidence,
            )
            .join(Tender, Tender.id == TenderBoqItem.tender_id)
            .where(
                TenderBoqItem.master_item_id == master_item_id,
                TenderBoqItem.inferred_unit_price.is_not(None),
            )
        )

        filters = []
        if ctx.sector_id:
            filters.append(Tender.primary_sector_id == ctx.sector_id)
        if ctx.region_id:
            filters.append(Tender.region_id == ctx.region_id)
        if ctx.government_entity_id:
            filters.append(Tender.government_entity_id == ctx.government_entity_id)
        if ctx.date_from:
            filters.append(Tender.award_date >= ctx.date_from)
        if ctx.date_to:
            filters.append(Tender.award_date <= ctx.date_to)
        if filters:
            stmt = stmt.where(and_(*filters))

        rows = self.db.execute(stmt).all()
        return [(float(p), float(c or 0.5)) for p, c in rows if p is not None]

    @staticmethod
    def _calculate_recommended(
        prices: list[float],
        weights: list[float],
        mean: float,
        median: float,
    ) -> float:
        """Recommend just-below-median to bias toward competitive pricing."""
        p40 = weighted_percentile(prices, weights, 40)
        return min(p40, (mean + median) / 2)


def _ctx_to_dict(ctx: ContextFilters) -> dict:
    return {
        "sector_id": str(ctx.sector_id) if ctx.sector_id else None,
        "region_id": str(ctx.region_id) if ctx.region_id else None,
        "government_entity_id": str(ctx.government_entity_id)
        if ctx.government_entity_id
        else None,
        "date_from": ctx.date_from.isoformat() if ctx.date_from else None,
        "date_to": ctx.date_to.isoformat() if ctx.date_to else None,
        "min_observations": ctx.min_observations,
    }
