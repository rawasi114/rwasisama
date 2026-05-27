"""Analytics engine schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReferencePriceResult(BaseModel):
    master_item_id: UUID | None = None
    available: bool
    weighted_mean: float | None = None
    weighted_median: float | None = None
    p25: float | None = None
    p75: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    std_deviation: float | None = None
    observation_count: int = 0
    recommended_for_rawasi: float | None = None
    context_used: dict = {}
    reason: str | None = None


class PricedItemOut(BaseModel):
    boq_item_id: UUID | None = None
    sequence_number: str | None = None
    description: str
    unit: str | None = None
    quantity: float
    master_item_id: UUID | None = None
    reference: ReferencePriceResult
    suggested_unit_price: float | None = None
    unit_price_range: tuple[float, float] | None = None
    suggested_total: float | None = None


class BoqPricingResult(BaseModel):
    items: list[PricedItemOut]
    total_recommended_value: float
    coverage_pct: float
    overall_confidence: float


class GoNoGoFactors(BaseModel):
    win_probability: float
    expected_margin: float
    strategic_value: float
    capacity_match: float
    effort_required: float
    cash_flow_impact: float


class GoNoGoResult(BaseModel):
    recommendation: Literal["GO", "REVIEW", "NO_GO"]
    confidence: Literal["high", "medium", "low"]
    composite_score: float = Field(..., ge=0, le=1)
    factor_scores: GoNoGoFactors
    reasoning: str
    top_concerns: list[str] = []
    top_strengths: list[str] = []


class CompetitorProfileOut(BaseModel):
    competitor_id: UUID
    analysis_period_months: int
    total_appearances: int
    total_wins: int
    win_rate: float
    avg_award_value: float | None = None
    median_award_value: float | None = None
    avg_discount_vs_reference_pct: float | None = None
    sector_distribution: dict
    region_distribution: dict
    entity_distribution: dict
    threat_score: int | None = None
    predicted_categories: list[str] = []


class CompetitorBidPrediction(BaseModel):
    competitor_id: UUID
    entry_probability: float
    estimated_bid_range: tuple[float, float] | None = None
    confidence: float


class WinProbabilityResult(BaseModel):
    probability: float
    confidence: float
    expected_competitors: list[UUID] = []
    sensitivity_analysis: list[dict] = []
    iterations: int
    runs_with_competition: int


class OptimalBidResult(BaseModel):
    recommended_bid: float
    expected_win_probability: float
    expected_margin_pct: float
    sensitivity_curve: list[dict] = []
