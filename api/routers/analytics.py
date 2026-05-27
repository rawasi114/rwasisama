"""Analytics endpoints exposing the four engines."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.core.errors import InsufficientDataError, NotFoundError
from api.schemas.analytics import (
    BoqPricingResult,
    CompetitorProfileOut,
    GoNoGoResult,
    OptimalBidResult,
    ReferencePriceResult,
    WinProbabilityResult,
)
from api.services.competitor_profiler import CompetitorProfileEngine
from api.services.go_no_go import GoNoGoEngine, GoNoGoInput
from api.services.reference_pricer import ContextFilters, ReferencePricingEngine
from api.services.win_probability import CompetitorScenario, WinProbabilityEngine

router = APIRouter(prefix="/analytics", tags=["analytics"])


class ReferenceQuery(BaseModel):
    master_item_id: UUID
    sector_id: UUID | None = None
    region_id: UUID | None = None
    government_entity_id: UUID | None = None
    min_observations: int = 3


@router.post("/reference-price", response_model=ReferencePriceResult)
def reference_price(query: ReferenceQuery, db: Session = Depends(get_db)) -> ReferencePriceResult:
    engine = ReferencePricingEngine(db)
    ctx = ContextFilters(
        sector_id=query.sector_id,
        region_id=query.region_id,
        government_entity_id=query.government_entity_id,
        min_observations=query.min_observations,
    )
    return engine.get_reference_price(query.master_item_id, ctx)


class BoqPricingRequest(BaseModel):
    items: list[dict]
    sector_id: UUID | None = None
    region_id: UUID | None = None
    government_entity_id: UUID | None = None


@router.post("/price-boq", response_model=BoqPricingResult)
def price_boq(request: BoqPricingRequest, db: Session = Depends(get_db)) -> BoqPricingResult:
    engine = ReferencePricingEngine(db)
    ctx = ContextFilters(
        sector_id=request.sector_id,
        region_id=request.region_id,
        government_entity_id=request.government_entity_id,
    )
    return engine.price_full_boq(request.items, ctx)


class GoNoGoPayload(BaseModel):
    estimated_award_value: float = Field(..., gt=0)
    expected_competitors: int = Field(..., ge=0)
    expected_margin_pct: float
    rawasi_capacity_load_pct: float = Field(..., ge=0, le=200)
    relationship_with_entity: str = "neutral"
    sector_strategic_priority: str = "medium"
    project_duration_days: int | None = None
    payment_terms_score: float = 0.5
    item_overlap_with_capacity_pct: float = 0.5
    requires_new_classification: bool = False
    win_probability: float = Field(..., ge=0, le=1)


@router.post("/go-no-go", response_model=GoNoGoResult)
def go_no_go(payload: GoNoGoPayload) -> GoNoGoResult:
    engine = GoNoGoEngine()
    input_ = GoNoGoInput(
        estimated_award_value=payload.estimated_award_value,
        expected_competitors=payload.expected_competitors,
        expected_margin_pct=payload.expected_margin_pct,
        rawasi_capacity_load_pct=payload.rawasi_capacity_load_pct,
        relationship_with_entity=payload.relationship_with_entity,
        sector_strategic_priority=payload.sector_strategic_priority,
        project_duration_days=payload.project_duration_days,
        payment_terms_score=payload.payment_terms_score,
        item_overlap_with_capacity_pct=payload.item_overlap_with_capacity_pct,
        requires_new_classification=payload.requires_new_classification,
    )
    return engine.evaluate(input_, payload.win_probability)


@router.get("/competitors/{competitor_id}/profile", response_model=CompetitorProfileOut)
def competitor_profile(
    competitor_id: UUID, period_months: int = 24, db: Session = Depends(get_db)
) -> CompetitorProfileOut:
    engine = CompetitorProfileEngine(db)
    try:
        return engine.build_profile(competitor_id, period_months)
    except (NotFoundError, InsufficientDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class CompetitorScenarioPayload(BaseModel):
    competitor_id: UUID
    entry_probability: float = Field(..., ge=0, le=1)
    bid_low: float = Field(..., gt=0)
    bid_high: float = Field(..., gt=0)


class WinProbabilityRequest(BaseModel):
    proposed_bid: float = Field(..., gt=0)
    technical_advantage: float = 0.0
    scenarios: list[CompetitorScenarioPayload]
    iterations: int | None = None


@router.post("/win-probability", response_model=WinProbabilityResult)
def win_probability(request: WinProbabilityRequest) -> WinProbabilityResult:
    engine = WinProbabilityEngine()
    scenarios = [
        CompetitorScenario(
            competitor_id=s.competitor_id,
            entry_probability=s.entry_probability,
            bid_low=s.bid_low,
            bid_high=s.bid_high,
        )
        for s in request.scenarios
    ]
    return engine.calculate(
        proposed_bid=request.proposed_bid,
        scenarios=scenarios,
        technical_advantage=request.technical_advantage,
        iterations=request.iterations,
    )


class OptimalBidRequest(BaseModel):
    reference_total: float = Field(..., gt=0)
    estimated_cost: float = Field(..., gt=0)
    scenarios: list[CompetitorScenarioPayload]
    technical_advantage: float = 0.0
    min_margin_pct: float = 0.03
    max_margin_pct: float = 0.25


@router.post("/optimal-bid", response_model=OptimalBidResult)
def optimal_bid(request: OptimalBidRequest) -> OptimalBidResult:
    engine = WinProbabilityEngine()
    scenarios = [
        CompetitorScenario(
            competitor_id=s.competitor_id,
            entry_probability=s.entry_probability,
            bid_low=s.bid_low,
            bid_high=s.bid_high,
        )
        for s in request.scenarios
    ]
    return engine.find_optimal_bid(
        scenarios=scenarios,
        reference_total=request.reference_total,
        estimated_cost=request.estimated_cost,
        technical_advantage=request.technical_advantage,
        min_margin_pct=request.min_margin_pct,
        max_margin_pct=request.max_margin_pct,
    )
