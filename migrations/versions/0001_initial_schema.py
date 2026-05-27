"""Initial schema for the Rawasi Pricing Intelligence System.

Creates all 19 tables described in the master spec (section 3).

Revision ID: 0001
Revises:
Create Date: 2026-05-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
        try:
            op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
        except Exception:
            # pgvector may not be available in some environments
            pass

    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.String(length=36)
    array_string_type = postgresql.ARRAY(sa.String()) if is_pg else sa.JSON()

    op.create_table(
        "government_entities",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200)),
        sa.Column("parent_id", uuid_type, sa.ForeignKey("government_entities.id")),
        sa.Column("sector_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("metadata", json_type),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_gov_entities_sector", "government_entities", ["sector_type"])
    op.create_index("ix_gov_entities_parent", "government_entities", ["parent_id"])

    op.create_table(
        "regions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cities",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(15), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100)),
        sa.Column("region_id", uuid_type, sa.ForeignKey("regions.id")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sectors",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(150), nullable=False),
        sa.Column("name_en", sa.String(150)),
        sa.Column("parent_id", uuid_type, sa.ForeignKey("sectors.id")),
        sa.Column("description_ar", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitors",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name_ar", sa.String(300), nullable=False),
        sa.Column("name_en", sa.String(300)),
        sa.Column("cr_number", sa.String(20), unique=True),
        sa.Column("unified_number", sa.String(20)),
        sa.Column("classification_grade", sa.String(20)),
        sa.Column("primary_sectors", array_string_type),
        sa.Column("primary_regions", array_string_type),
        sa.Column("estimated_capacity_tier", sa.String(20)),
        sa.Column("relationship_type", sa.String(30)),
        sa.Column("threat_level", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("first_seen_date", sa.Date),
        sa.Column("last_seen_date", sa.Date),
        sa.Column("total_wins_observed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_appearances", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("metadata", json_type),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "threat_level IS NULL OR (threat_level BETWEEN 1 AND 10)",
            name="ck_competitors_threat_level_range",
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("full_name_ar", sa.String(200)),
        sa.Column("full_name_en", sa.String(200)),
        sa.Column("role", sa.String(30), nullable=False, server_default="reader"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "master_item_categories",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(30), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(150), nullable=False),
        sa.Column("name_en", sa.String(150)),
        sa.Column("parent_id", uuid_type, sa.ForeignKey("master_item_categories.id")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    master_items_cols = [
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(30), unique=True, nullable=False),
        sa.Column("name_ar", sa.String(500), nullable=False),
        sa.Column("name_en", sa.String(500)),
        sa.Column("description_ar", sa.Text),
        sa.Column("description_en", sa.Text),
        sa.Column("category_id", uuid_type, sa.ForeignKey("master_item_categories.id")),
        sa.Column("parent_item_id", uuid_type, sa.ForeignKey("master_items.id")),
        sa.Column("default_unit", sa.String(20), nullable=False),
        sa.Column("alternative_units", array_string_type),
        sa.Column("specifications", json_type),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used_date", sa.Date),
        sa.Column("confidence_baseline", sa.Numeric(3, 2), nullable=False, server_default="0.5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]
    # Embedding column — added only in PG with pgvector
    if is_pg:
        master_items_cols.append(sa.Column("embedding", sa.Text))  # placeholder; convert below
    else:
        master_items_cols.append(sa.Column("embedding", sa.Text))

    op.create_table("master_items", *master_items_cols)
    if is_pg:
        # Convert embedding text column to vector(1536) if pgvector available
        try:
            op.execute("ALTER TABLE master_items ALTER COLUMN embedding TYPE vector(1536) USING NULL")
        except Exception:
            pass

    op.create_table(
        "master_item_synonyms",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "master_item_id",
            uuid_type,
            sa.ForeignKey("master_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("synonym_text", sa.Text, nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("occurrence_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("last_seen_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_synonyms_master", "master_item_synonyms", ["master_item_id"])

    op.create_table(
        "tenders",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("etimad_tender_id", sa.String(50), unique=True),
        sa.Column("internal_reference", sa.String(50), unique=True),
        sa.Column("title_ar", sa.String(1000), nullable=False),
        sa.Column("title_en", sa.String(1000)),
        sa.Column("description_ar", sa.Text),
        sa.Column("government_entity_id", uuid_type, sa.ForeignKey("government_entities.id"), nullable=False),
        sa.Column("sub_entity_name", sa.String(300)),
        sa.Column("region_id", uuid_type, sa.ForeignKey("regions.id")),
        sa.Column("city_id", uuid_type, sa.ForeignKey("cities.id")),
        sa.Column("project_site_details", sa.Text),
        sa.Column("primary_sector_id", uuid_type, sa.ForeignKey("sectors.id")),
        sa.Column("secondary_sectors", array_string_type),
        sa.Column("required_classification_grade", sa.String(20)),
        sa.Column("requires_pre_qualification", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("publication_date", sa.Date),
        sa.Column("submission_deadline", sa.Date),
        sa.Column("bid_opening_date", sa.Date),
        sa.Column("award_date", sa.Date, nullable=False),
        sa.Column("execution_duration_days", sa.Integer),
        sa.Column("bid_bond_value", sa.Numeric(15, 2)),
        sa.Column("award_value", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "awarded_to_competitor_id", uuid_type, sa.ForeignKey("competitors.id"), nullable=False
        ),
        sa.Column("total_bidders_count", sa.Integer),
        sa.Column("rawasi_participated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("rawasi_bid_id", sa.String(36)),
        sa.Column("data_quality_score", sa.Numeric(3, 2)),
        sa.Column("has_full_boq", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("has_award_announcement", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("boq_extraction_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text),
        sa.Column("entered_by_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("verified_by_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("verification_date", sa.Date),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("metadata", json_type),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenders_entity", "tenders", ["government_entity_id"])
    op.create_index("ix_tenders_region", "tenders", ["region_id"])
    op.create_index("ix_tenders_award_date", "tenders", ["award_date"])
    op.create_index("ix_tenders_sector", "tenders", ["primary_sector_id"])
    op.create_index("ix_tenders_winner", "tenders", ["awarded_to_competitor_id"])

    op.create_table(
        "tender_files",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("tender_id", uuid_type, sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_type", sa.String(30), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tender_boq_items",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("tender_id", uuid_type, sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.String(20)),
        sa.Column("original_description", sa.Text, nullable=False),
        sa.Column("original_unit", sa.String(20)),
        sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
        sa.Column("unit_estimated_price", sa.Numeric(15, 2)),
        sa.Column("master_item_id", uuid_type, sa.ForeignKey("master_items.id")),
        sa.Column("matching_confidence", sa.Numeric(3, 2)),
        sa.Column("matching_method", sa.String(30)),
        sa.Column("matched_at", sa.DateTime),
        sa.Column("matched_by_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("requires_manual_review", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("inferred_unit_price", sa.Numeric(15, 2)),
        sa.Column("inferred_total_price", sa.Numeric(15, 2)),
        sa.Column("inference_confidence", sa.Numeric(3, 2)),
        sa.Column("inference_method", sa.String(50)),
        sa.Column("inferred_at", sa.DateTime),
        sa.Column("item_category", sa.String(50)),
        sa.Column("is_high_volume", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("volume_share_pct", sa.Numeric(5, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_boq_tender", "tender_boq_items", ["tender_id"])
    op.create_index("ix_boq_master_item", "tender_boq_items", ["master_item_id"])

    op.create_table(
        "tender_bidders",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("tender_id", uuid_type, sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("competitor_id", uuid_type, sa.ForeignKey("competitors.id")),
        sa.Column("bidder_name_as_appeared", sa.String(500), nullable=False),
        sa.Column("bid_amount", sa.Numeric(15, 2)),
        sa.Column("bid_rank", sa.Integer),
        sa.Column("was_qualified", sa.Boolean),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("notes", sa.Text),
        sa.UniqueConstraint("tender_id", "bidder_name_as_appeared", name="uq_tender_bidder_name"),
    )

    op.create_table(
        "tender_classifications",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("tender_id", uuid_type, sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("classification_type", sa.String(50), nullable=False),
        sa.Column("classification_value", sa.String(100), nullable=False),
    )

    op.create_table(
        "rawasi_bids",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("tender_id", uuid_type, sa.ForeignKey("tenders.id"), nullable=False),
        sa.Column("bid_total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("bid_submission_date", sa.Date),
        sa.Column("final_rank", sa.Integer),
        sa.Column("won", sa.Boolean, nullable=False),
        sa.Column("pricing_strategy", sa.String(50)),
        sa.Column("target_margin_pct", sa.Numeric(5, 2)),
        sa.Column("actual_margin_pct", sa.Numeric(5, 2)),
        sa.Column("post_mortem_notes", sa.Text),
        sa.Column("lessons_learned", sa.Text),
        sa.Column("boq_file_path", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tender_id", name="uq_rawasi_bid_tender"),
    )

    op.create_table(
        "rawasi_bid_items",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "rawasi_bid_id",
            uuid_type,
            sa.ForeignKey("rawasi_bids.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tender_boq_item_id", uuid_type, sa.ForeignKey("tender_boq_items.id")),
        sa.Column("master_item_id", uuid_type, sa.ForeignKey("master_items.id")),
        sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("cost_breakdown", json_type),
        sa.Column("estimated_cost", sa.Numeric(15, 2)),
        sa.Column("margin_amount", sa.Numeric(15, 2)),
        sa.Column("margin_pct", sa.Numeric(5, 2)),
        sa.Column("winner_unit_price_inferred", sa.Numeric(15, 2)),
        sa.Column("diff_from_winner_pct", sa.Numeric(5, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_profiles",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "competitor_id",
            uuid_type,
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analysis_period_months", sa.Integer, nullable=False),
        sa.Column("last_calculated_at", sa.DateTime, nullable=False),
        sa.Column("total_appearances", sa.Integer),
        sa.Column("total_wins", sa.Integer),
        sa.Column("win_rate", sa.Numeric(5, 2)),
        sa.Column("avg_award_value", sa.Numeric(15, 2)),
        sa.Column("median_award_value", sa.Numeric(15, 2)),
        sa.Column("avg_discount_vs_reference_pct", sa.Numeric(5, 2)),
        sa.Column("discount_variance", sa.Numeric(5, 2)),
        sa.Column("sector_distribution", json_type),
        sa.Column("region_distribution", json_type),
        sa.Column("entity_distribution", json_type),
        sa.Column("min_won_value", sa.Numeric(15, 2)),
        sa.Column("max_won_value", sa.Numeric(15, 2)),
        sa.Column("avg_won_value", sa.Numeric(15, 2)),
        sa.Column("item_pricing_patterns", json_type),
        sa.Column("predicted_appearance_categories", array_string_type),
        sa.Column("threat_score", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "competitor_id", "analysis_period_months", name="uq_competitor_profile_period"
        ),
        sa.CheckConstraint(
            "threat_score IS NULL OR (threat_score BETWEEN 1 AND 100)",
            name="ck_competitor_profiles_threat_score_range",
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", uuid_type),
        sa.Column("before_state", json_type),
        sa.Column("after_state", json_type),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "data_quality_issues",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", uuid_type, nullable=False),
        sa.Column("issue_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("resolved_by_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "data_quality_issues",
        "audit_log",
        "competitor_profiles",
        "rawasi_bid_items",
        "rawasi_bids",
        "tender_classifications",
        "tender_bidders",
        "tender_boq_items",
        "tender_files",
        "tenders",
        "master_item_synonyms",
        "master_items",
        "master_item_categories",
        "users",
        "competitors",
        "sectors",
        "cities",
        "regions",
        "government_entities",
    ]:
        op.drop_table(table)
