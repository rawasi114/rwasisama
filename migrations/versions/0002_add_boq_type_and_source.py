"""Add boq_type and source tracking to tender_boq_items.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOQ_TYPES = ("original_tender", "rawasi", "competitor")


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = (
        postgresql.UUID(as_uuid=True) if bind.dialect.name == "postgresql" else sa.String(36)
    )

    op.add_column(
        "tender_boq_items",
        sa.Column(
            "boq_type",
            sa.String(30),
            nullable=False,
            server_default="original_tender",
        ),
    )
    op.add_column(
        "tender_boq_items",
        sa.Column("source_file_id", uuid_type, sa.ForeignKey("tender_files.id")),
    )
    op.add_column(
        "tender_boq_items",
        sa.Column(
            "source_competitor_id", uuid_type, sa.ForeignKey("competitors.id")
        ),
    )
    op.create_check_constraint(
        "ck_tender_boq_items_boq_type",
        "tender_boq_items",
        f"boq_type IN {BOQ_TYPES!r}".replace("'", "'"),
    )
    op.create_index(
        "ix_boq_type", "tender_boq_items", ["boq_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_boq_type", table_name="tender_boq_items")
    op.drop_constraint("ck_tender_boq_items_boq_type", "tender_boq_items")
    op.drop_column("tender_boq_items", "source_competitor_id")
    op.drop_column("tender_boq_items", "source_file_id")
    op.drop_column("tender_boq_items", "boq_type")
