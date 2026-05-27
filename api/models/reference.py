"""Reference tables: government entities, regions, cities, sectors."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models._types import JsonField
from api.models.base import Base, TimestampMixin, UUIDPKMixin


class GovernmentEntity(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "government_entities"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("government_entities.id"), nullable=True
    )
    sector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JsonField)

    parent: Mapped[GovernmentEntity | None] = relationship(
        "GovernmentEntity",
        remote_side="GovernmentEntity.id",
        backref="children",
    )


class Region(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class City(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cities"

    code: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    region_id: Mapped[UUID | None] = mapped_column(ForeignKey("regions.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    region: Mapped[Region | None] = relationship("Region")


class Sector(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sectors"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(150))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("sectors.id"))
    description_ar: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[Sector | None] = relationship(
        "Sector",
        remote_side="Sector.id",
        backref="children",
    )
