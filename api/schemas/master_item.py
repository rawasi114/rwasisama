"""Master item schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MasterItemBase(BaseModel):
    code: str = Field(..., max_length=30)
    name_ar: str = Field(..., max_length=500)
    name_en: str | None = None
    description_ar: str | None = None
    description_en: str | None = None
    default_unit: str
    alternative_units: list[str] | None = None
    specifications: dict | None = None
    confidence_baseline: float = 0.5


class MasterItemCreate(MasterItemBase):
    category_id: UUID | None = None
    parent_item_id: UUID | None = None


class MasterItemOut(MasterItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID | None = None
    parent_item_id: UUID | None = None
    usage_count: int
    last_used_date: date | None = None
    is_active: bool


class MasterItemSynonymCreate(BaseModel):
    master_item_id: UUID
    synonym_text: str
    source: str = "manual"


class MasterItemSynonymOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    master_item_id: UUID
    synonym_text: str
    source: str
    occurrence_count: int
