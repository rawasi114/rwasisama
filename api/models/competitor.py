"""Competitor and competitor profile tables."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.models._types import JsonField, StringArray
from api.models.base import Base, TimestampMixin, UUIDPKMixin


class Competitor(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "competitors"

    name_ar: Mapped[str] = mapped_column(String(300), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(300))
    cr_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    unified_number: Mapped[str | None] = mapped_column(String(20))

    classification_grade: Mapped[str | None] = mapped_column(String(20))
    primary_sectors: Mapped[list[str] | None] = mapped_column(StringArray)
    primary_regions: Mapped[list[str] | None] = mapped_column(StringArray)
    estimated_capacity_tier: Mapped[str | None] = mapped_column(String(20))

    relationship_type: Mapped[str | None] = mapped_column(String(30))
    threat_level: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    first_seen_date: Mapped[date | None] = mapped_column(Date)
    last_seen_date: Mapped[date | None] = mapped_column(Date)
    total_wins_observed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_appearances: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JsonField)

    __table_args__ = (
        CheckConstraint(
            "threat_level IS NULL OR (threat_level BETWEEN 1 AND 10)",
            name="ck_competitors_threat_level_range",
        ),
    )


class CompetitorProfile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "competitor_profiles"

    competitor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    analysis_period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    total_appearances: Mapped[int | None] = mapped_column(Integer)
    total_wins: Mapped[int | None] = mapped_column(Integer)
    win_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    avg_award_value: Mapped[float | None] = mapped_column(Numeric(15, 2))
    median_award_value: Mapped[float | None] = mapped_column(Numeric(15, 2))

    avg_discount_vs_reference_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    discount_variance: Mapped[float | None] = mapped_column(Numeric(5, 2))

    sector_distribution: Mapped[dict | None] = mapped_column(JsonField)
    region_distribution: Mapped[dict | None] = mapped_column(JsonField)
    entity_distribution: Mapped[dict | None] = mapped_column(JsonField)

    min_won_value: Mapped[float | None] = mapped_column(Numeric(15, 2))
    max_won_value: Mapped[float | None] = mapped_column(Numeric(15, 2))
    avg_won_value: Mapped[float | None] = mapped_column(Numeric(15, 2))

    item_pricing_patterns: Mapped[dict | None] = mapped_column(JsonField)

    predicted_appearance_categories: Mapped[list[str] | None] = mapped_column(StringArray)
    threat_score: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint(
            "competitor_id",
            "analysis_period_months",
            name="uq_competitor_profile_period",
        ),
        CheckConstraint(
            "threat_score IS NULL OR (threat_score BETWEEN 1 AND 100)",
            name="ck_competitor_profiles_threat_score_range",
        ),
    )
