"""Rawasi's own bid history tables."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models._types import JsonField
from api.models.base import Base, TimestampMixin, UUIDPKMixin


class RawasiBid(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "rawasi_bids"

    tender_id: Mapped[UUID] = mapped_column(ForeignKey("tenders.id"), nullable=False)

    bid_total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    bid_submission_date: Mapped[date | None] = mapped_column(Date)
    final_rank: Mapped[int | None] = mapped_column(Integer)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False)

    pricing_strategy: Mapped[str | None] = mapped_column(String(50))
    target_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    actual_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    post_mortem_notes: Mapped[str | None] = mapped_column(Text)
    lessons_learned: Mapped[str | None] = mapped_column(Text)

    boq_file_path: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list[RawasiBidItem]] = relationship(
        "RawasiBidItem",
        back_populates="rawasi_bid",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("tender_id", name="uq_rawasi_bid_tender"),)


class RawasiBidItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "rawasi_bid_items"

    rawasi_bid_id: Mapped[UUID] = mapped_column(
        ForeignKey("rawasi_bids.id", ondelete="CASCADE"), nullable=False
    )
    tender_boq_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("tender_boq_items.id"))
    master_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("master_items.id"))

    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    cost_breakdown: Mapped[dict | None] = mapped_column(JsonField)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(15, 2))
    margin_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    winner_unit_price_inferred: Mapped[float | None] = mapped_column(Numeric(15, 2))
    diff_from_winner_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    notes: Mapped[str | None] = mapped_column(Text)

    rawasi_bid: Mapped[RawasiBid] = relationship("RawasiBid", back_populates="items")
