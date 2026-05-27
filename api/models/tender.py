"""Tender / BoQ / Bidder tables."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models._types import JsonField, StringArray
from api.models.base import Base, TimestampMixin, UUIDPKMixin


class Tender(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tenders"

    etimad_tender_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    internal_reference: Mapped[str | None] = mapped_column(String(50), unique=True)

    title_ar: Mapped[str] = mapped_column(String(1000), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Text)

    government_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("government_entities.id"), nullable=False
    )
    sub_entity_name: Mapped[str | None] = mapped_column(String(300))
    region_id: Mapped[UUID | None] = mapped_column(ForeignKey("regions.id"))
    city_id: Mapped[UUID | None] = mapped_column(ForeignKey("cities.id"))
    project_site_details: Mapped[str | None] = mapped_column(Text)

    primary_sector_id: Mapped[UUID | None] = mapped_column(ForeignKey("sectors.id"))
    secondary_sectors: Mapped[list[UUID] | None] = mapped_column(StringArray)
    required_classification_grade: Mapped[str | None] = mapped_column(String(20))
    requires_pre_qualification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    publication_date: Mapped[date | None] = mapped_column(Date)
    submission_deadline: Mapped[date | None] = mapped_column(Date)
    bid_opening_date: Mapped[date | None] = mapped_column(Date)
    award_date: Mapped[date] = mapped_column(Date, nullable=False)
    execution_duration_days: Mapped[int | None] = mapped_column(Integer)

    bid_bond_value: Mapped[float | None] = mapped_column(Numeric(15, 2))
    award_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    awarded_to_competitor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competitors.id"), nullable=False
    )
    total_bidders_count: Mapped[int | None] = mapped_column(Integer)

    rawasi_participated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rawasi_bid_id: Mapped[UUID | None] = mapped_column(String(36))

    data_quality_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    has_full_boq: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_award_announcement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    boq_extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    entered_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    verification_date: Mapped[date | None] = mapped_column(Date)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JsonField)

    boq_items: Mapped[list[TenderBoqItem]] = relationship(
        "TenderBoqItem",
        back_populates="tender",
        cascade="all, delete-orphan",
    )
    bidders: Mapped[list[TenderBidder]] = relationship(
        "TenderBidder",
        back_populates="tender",
        cascade="all, delete-orphan",
    )
    files: Mapped[list[TenderFile]] = relationship(
        "TenderFile",
        back_populates="tender",
        cascade="all, delete-orphan",
    )


class TenderFile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tender_files"

    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    tender: Mapped[Tender] = relationship("Tender", back_populates="files")


class TenderBoqItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tender_boq_items"

    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )

    sequence_number: Mapped[str | None] = mapped_column(String(20))
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    original_unit: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    unit_estimated_price: Mapped[float | None] = mapped_column(Numeric(15, 2))

    master_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("master_items.id"))
    matching_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    matching_method: Mapped[str | None] = mapped_column(String(30))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime)
    matched_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    inferred_unit_price: Mapped[float | None] = mapped_column(Numeric(15, 2))
    inferred_total_price: Mapped[float | None] = mapped_column(Numeric(15, 2))
    inference_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    inference_method: Mapped[str | None] = mapped_column(String(50))
    inferred_at: Mapped[datetime | None] = mapped_column(DateTime)

    item_category: Mapped[str | None] = mapped_column(String(50))
    is_high_volume: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    volume_share_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    boq_type: Mapped[str] = mapped_column(
        String(30), default="original_tender", nullable=False
    )
    source_file_id: Mapped[UUID | None] = mapped_column(ForeignKey("tender_files.id"))
    source_competitor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("competitors.id")
    )

    notes: Mapped[str | None] = mapped_column(Text)

    tender: Mapped[Tender] = relationship("Tender", back_populates="boq_items")


class TenderBidder(UUIDPKMixin, Base):
    __tablename__ = "tender_bidders"

    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[UUID | None] = mapped_column(ForeignKey("competitors.id"))
    bidder_name_as_appeared: Mapped[str] = mapped_column(String(500), nullable=False)
    bid_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    bid_rank: Mapped[int | None] = mapped_column(Integer)
    was_qualified: Mapped[bool | None] = mapped_column(Boolean)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    tender: Mapped[Tender] = relationship("Tender", back_populates="bidders")

    __table_args__ = (
        UniqueConstraint("tender_id", "bidder_name_as_appeared", name="uq_tender_bidder_name"),
    )


class TenderClassification(UUIDPKMixin, Base):
    __tablename__ = "tender_classifications"

    tender_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    classification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    classification_value: Mapped[str] = mapped_column(String(100), nullable=False)
