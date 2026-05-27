"""Cross-dialect column type adapters.

Production uses PostgreSQL-native types (JSONB, ARRAY); tests use SQLite
which doesn't support either. ``StringArray`` and ``JsonField`` return the
right SQLAlchemy type per dialect.
"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import TypeDecorator


class StringArray(TypeDecorator):
    """Variable-length array of strings — PG ARRAY, SQLite JSON."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String()))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


class JsonField(TypeDecorator):
    """JSON document — PG JSONB, SQLite JSON."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value
