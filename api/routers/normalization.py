"""Normalization API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.schemas.normalization import (
    NormalizationMatchOut,
    NormalizationRequest,
    NormalizationResult,
)
from api.services.boq_normalizer import BoqNormalizer

router = APIRouter(prefix="/normalize", tags=["normalization"])


@router.post("/item", response_model=NormalizationResult)
def normalize_item(
    request: NormalizationRequest, db: Session = Depends(get_db)
) -> NormalizationResult:
    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        description=request.description,
        unit=request.unit,
        use_claude=request.use_claude,
    )
    candidates = [
        NormalizationMatchOut(
            master_item_id=c.master_item_id,
            master_item_code=c.master_item_code,
            master_item_name_ar=c.master_item_name_ar,
            similarity=c.similarity,
        )
        for c in outcome.top_candidates
    ]
    return NormalizationResult(
        match_found=outcome.match_found,
        master_item_id=outcome.master_item_id,
        master_item_code=outcome.master_item_code,
        confidence=outcome.confidence,
        method=outcome.method,
        requires_manual_review=outcome.requires_manual_review,
        top_candidates=candidates,
        reasoning=outcome.reasoning,
    )
