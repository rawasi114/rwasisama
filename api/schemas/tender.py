"""Tender / BoQ schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BoqItemIn(BaseModel):
    sequence_number: str | None = None
    original_description: str
    original_unit: str | None = None
    quantity: float = Field(..., gt=0)
    unit_estimated_price: float | None = Field(default=None, ge=0)
    item_category: str | None = None
    notes: str | None = None


class BoqItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tender_id: UUID
    sequence_number: str | None = None
    original_description: str
    original_unit: str | None = None
    quantity: float
    unit_estimated_price: float | None = None
    master_item_id: UUID | None = None
    matching_confidence: float | None = None
    matching_method: str | None = None
    requires_manual_review: bool
    inferred_unit_price: float | None = None
    inferred_total_price: float | None = None
    inference_confidence: float | None = None
    inference_method: str | None = None
    item_category: str | None = None
    is_high_volume: bool
    volume_share_pct: float | None = None


class TenderBidderIn(BaseModel):
    bidder_name_as_appeared: str
    competitor_id: UUID | None = None
    bid_amount: float | None = Field(default=None, ge=0)
    bid_rank: int | None = Field(default=None, ge=1)
    was_qualified: bool | None = None
    rejection_reason: str | None = None
    notes: str | None = None


class TenderBidderOut(TenderBidderIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tender_id: UUID


class TenderBase(BaseModel):
    etimad_tender_id: str | None = None
    internal_reference: str | None = None
    title_ar: str
    title_en: str | None = None
    description_ar: str | None = None

    government_entity_id: UUID
    sub_entity_name: str | None = None
    region_id: UUID | None = None
    city_id: UUID | None = None
    project_site_details: str | None = None

    primary_sector_id: UUID | None = None
    secondary_sectors: list[UUID] | None = None
    required_classification_grade: str | None = None
    requires_pre_qualification: bool = False

    publication_date: date | None = None
    submission_deadline: date | None = None
    bid_opening_date: date | None = None
    award_date: date
    execution_duration_days: int | None = Field(default=None, ge=1)

    bid_bond_value: float | None = Field(default=None, ge=0)
    award_value: float = Field(..., gt=0)
    awarded_to_competitor_id: UUID
    total_bidders_count: int | None = Field(default=None, ge=0)

    rawasi_participated: bool = False

    notes: str | None = None

    @field_validator("award_value")
    @classmethod
    def _validate_award_value(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("award_value must be > 0")
        return v


class TenderCreate(TenderBase):
    boq_items: list[BoqItemIn] = Field(default_factory=list)
    bidders: list[TenderBidderIn] = Field(default_factory=list)


class TenderUpdate(BaseModel):
    title_ar: str | None = None
    notes: str | None = None
    award_value: float | None = Field(default=None, gt=0)
    awarded_to_competitor_id: UUID | None = None
    has_full_boq: bool | None = None
    has_award_announcement: bool | None = None
    boq_extraction_status: str | None = None
    is_archived: bool | None = None


class TenderOut(TenderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    data_quality_score: float | None = None
    has_full_boq: bool
    has_award_announcement: bool
    boq_extraction_status: str
    is_archived: bool
