"""Pytest fixtures.

Tests run against an in-memory SQLite database to avoid requiring PostgreSQL
locally. The production schema is created from the SQLAlchemy metadata
directly (Alembic migrations target real PG features pgvector / JSONB GIN).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest

# Ensure environment is set before any imports that read settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.core import database as core_db
from api.models import (
    Base,
    Competitor,
    GovernmentEntity,
    MasterItem,
    Region,
    Sector,
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine, monkeypatch) -> Generator[Session, None, None]:
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = SessionFactory()

    # Monkey-patch the global SessionLocal & get_db dependency
    monkeypatch.setattr(core_db, "SessionLocal", SessionFactory)
    monkeypatch.setattr(core_db, "engine", engine)

    def _override_get_db():
        yield session

    from api.main import app as fastapi_app

    fastapi_app.dependency_overrides[core_db.get_db] = _override_get_db

    try:
        yield session
    finally:
        fastapi_app.dependency_overrides.pop(core_db.get_db, None)
        session.close()
        with engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()


@pytest.fixture
def seed_entities(db: Session) -> dict:
    """Seed minimal reference data for service tests."""
    region = Region(code="EP", name_ar="المنطقة الشرقية")
    entity = GovernmentEntity(code="NG", name_ar="الحرس الوطني", sector_type="military")
    sector = Sector(code="FURN", name_ar="أثاث")
    competitor = Competitor(name_ar="شركة الديار للأثاث")
    db.add_all([region, entity, sector, competitor])
    db.flush()
    return {
        "region": region,
        "entity": entity,
        "sector": sector,
        "competitor": competitor,
    }


@pytest.fixture
def seed_master_items(db: Session) -> dict[str, MasterItem]:
    items = [
        MasterItem(code="CONC-RC-30", name_ar="خرسانة مسلحة بمقاومة 30 ميجا", default_unit="m3"),
        MasterItem(code="STEEL-REBAR-Y12", name_ar="حديد تسليح قطر 12 مم", default_unit="ton"),
        MasterItem(code="PAINT-INT-PLST", name_ar="دهان بلاستيكي داخلي درجة أولى", default_unit="m2"),
        MasterItem(code="FURN-DESK-EXEC", name_ar="مكتب تنفيذي قياس كبير", default_unit="no"),
    ]
    db.add_all(items)
    db.flush()
    return {it.code: it for it in items}


@pytest.fixture
def today() -> date:
    return date(2026, 5, 27)
