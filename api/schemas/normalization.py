"""Normalization request/response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class NormalizationRequest(BaseModel):
    description: str
    unit: str | None = None
    use_claude: bool = True


class NormalizationMatchOut(BaseModel):
    master_item_id: UUID
    master_item_code: str
    master_item_name_ar: str
    similarity: float


class NormalizationResult(BaseModel):
    match_found: bool
    master_item_id: UUID | None = None
    master_item_code: str | None = None
    confidence: float
    method: str
    requires_manual_review: bool = False
    top_candidates: list[NormalizationMatchOut] = []
    reasoning: str | None = None
