"""Pydantic schemas for the BoQ import endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BoqTypeLiteral = Literal["original_tender", "rawasi", "competitor"]


class StagedBoqItemPayload(BaseModel):
    """One row in the review-and-confirm payload."""

    model_config = ConfigDict(populate_by_name=True)

    sequence_number: str | None = None
    description: str
    unit: str | None = None
    quantity: float = Field(..., gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    total_price: float | None = Field(default=None, ge=0)
    master_item_id: UUID | None = None
    master_item_code: str | None = None
    matching_confidence: float = 0.0
    matching_method: str = "none"
    requires_manual_review: bool = False


class BoqImportPreviewResponse(BaseModel):
    tender_id: UUID
    boq_type: BoqTypeLiteral
    source_file_id: UUID
    source_competitor_id: UUID | None = None
    parser: str
    total_items: int
    items_needing_review: int
    items: list[StagedBoqItemPayload]
    warnings: list[str] = []


class BoqImportConfirmRequest(BaseModel):
    boq_type: BoqTypeLiteral
    source_file_id: UUID | None = None
    source_competitor_id: UUID | None = None
    items: list[StagedBoqItemPayload]


class BoqImportConfirmResponse(BaseModel):
    tender_id: UUID
    boq_type: BoqTypeLiteral
    items_committed: int
