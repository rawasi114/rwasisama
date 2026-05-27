"""Operational tables: users, audit log, data quality issues."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.models._types import JsonField
from api.models.base import Base, TimestampMixin, UUIDPKMixin


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    full_name_ar: Mapped[str | None] = mapped_column(String(200))
    full_name_en: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="reader")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(UUIDPKMixin, Base):
    __tablename__ = "audit_log"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column()
    before_state: Mapped[dict | None] = mapped_column(JsonField)
    after_state: Mapped[dict | None] = mapped_column(JsonField)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DataQualityIssue(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "data_quality_issues"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
