"""Master item dictionary tables — the heart of the normalization layer."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.config import get_settings
from api.models._types import JsonField, StringArray
from api.models.base import Base, TimestampMixin, UUIDPKMixin


def _embedding_column():
    """Return a Vector column on PG with pgvector, JSON otherwise.

    The fallback lets the model load under SQLite for unit testing.
    """
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        return mapped_column(JsonField, nullable=True)
    dim = get_settings().embedding_dimension
    try:
        return mapped_column(Vector(dim), nullable=True)
    except Exception:
        return mapped_column(JsonField, nullable=True)


class MasterItemCategory(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "master_item_categories"

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(150))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("master_item_categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[MasterItemCategory | None] = relationship(
        "MasterItemCategory",
        remote_side="MasterItemCategory.id",
        backref="children",
    )


class MasterItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "master_items"

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(500), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(500))
    description_ar: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)

    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("master_item_categories.id"))
    parent_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("master_items.id"))

    default_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    alternative_units: Mapped[list[str] | None] = mapped_column(StringArray)
    specifications: Mapped[dict | None] = mapped_column(JsonField)

    embedding = _embedding_column()

    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_date: Mapped[date | None] = mapped_column(Date)
    confidence_baseline: Mapped[float] = mapped_column(
        Numeric(3, 2), default=0.5, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[MasterItemCategory | None] = relationship("MasterItemCategory")
    synonyms: Mapped[list[MasterItemSynonym]] = relationship(
        "MasterItemSynonym",
        back_populates="master_item",
        cascade="all, delete-orphan",
    )


class MasterItemSynonym(UUIDPKMixin, Base):
    __tablename__ = "master_item_synonyms"

    master_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("master_items.id", ondelete="CASCADE"), nullable=False
    )
    synonym_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_seen_date: Mapped[date | None] = mapped_column(Date)

    master_item: Mapped[MasterItem] = relationship("MasterItem", back_populates="synonyms")
