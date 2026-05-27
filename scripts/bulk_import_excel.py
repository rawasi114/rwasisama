"""Bulk-import tenders from the standard Excel template.

Usage:
    python -m scripts.bulk_import_excel path/to/tenders.xlsx [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.database import SessionLocal
from api.core.errors import ValidationError
from api.core.logging import configure_logging, get_logger
from api.models import Competitor, GovernmentEntity, Region, Sector
from api.schemas.tender import TenderBidderIn, TenderCreate
from api.services.tender_service import TenderService

LOG = get_logger(__name__)

REQUIRED_COLUMNS = {
    "etimad_id",
    "title_ar",
    "government_entity_code",
    "award_date",
    "award_value",
    "winner_name",
    "rawasi_participated",
}


@dataclass
class ImportResult:
    total_rows: int
    imported: int
    skipped: int
    errors: list[str]


def load_workbook(path: Path) -> dict[str, pd.DataFrame]:
    sheets = pd.read_excel(path, sheet_name=None)
    return {name: df for name, df in sheets.items()}


def validate_columns(df: pd.DataFrame) -> list[str]:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return [f"Missing required columns: {sorted(missing)}"]
    return []


def lookup_government_entity(db: Session, code: str) -> GovernmentEntity:
    entity = db.execute(
        select(GovernmentEntity).where(GovernmentEntity.code == code)
    ).scalar_one_or_none()
    if entity is None:
        raise ValidationError(f"government_entity_code={code!r} not found")
    return entity


def lookup_region(db: Session, code: str | None) -> Region | None:
    if not code:
        return None
    return db.execute(
        select(Region).where(Region.code == code)
    ).scalar_one_or_none()


def lookup_sector(db: Session, code: str | None) -> Sector | None:
    if not code:
        return None
    return db.execute(
        select(Sector).where(Sector.code == code)
    ).scalar_one_or_none()


def find_or_create_competitor(db: Session, name: str) -> Competitor:
    competitor = db.execute(
        select(Competitor).where(Competitor.name_ar == name)
    ).scalar_one_or_none()
    if competitor is None:
        competitor = Competitor(name_ar=name)
        db.add(competitor)
        db.flush()
    return competitor


def _parse_bidders(df: pd.DataFrame | None, etimad_id: str) -> list[TenderBidderIn]:
    if df is None or df.empty:
        return []
    bidders: list[TenderBidderIn] = []
    matching = df[df["tender_etimad_id"].astype(str) == str(etimad_id)]
    for _, row in matching.iterrows():
        bidders.append(
            TenderBidderIn(
                bidder_name_as_appeared=str(row["bidder_name"]),
                bid_amount=float(row.get("bid_amount") or 0) or None,
                bid_rank=int(row["rank"]) if not pd.isna(row.get("rank")) else None,
            )
        )
    return bidders


def _row_to_tender_create(
    db: Session,
    row: pd.Series,
    bidders_df: pd.DataFrame | None,
) -> TenderCreate:
    entity = lookup_government_entity(db, str(row["government_entity_code"]))
    region = lookup_region(db, _safe_str(row.get("region_code")))
    sector = lookup_sector(db, _safe_str(row.get("sector_code")))
    winner = find_or_create_competitor(db, str(row["winner_name"]))

    bidders = _parse_bidders(bidders_df, str(row["etimad_id"]))

    return TenderCreate(
        etimad_tender_id=str(row["etimad_id"]),
        title_ar=str(row["title_ar"]),
        government_entity_id=entity.id,
        region_id=region.id if region else None,
        primary_sector_id=sector.id if sector else None,
        award_date=_to_date(row["award_date"]),
        award_value=float(row["award_value"]),
        awarded_to_competitor_id=winner.id,
        rawasi_participated=bool(row["rawasi_participated"]),
        total_bidders_count=int(row["total_bidders"]) if not pd.isna(row.get("total_bidders")) else None,
        notes=_safe_str(row.get("notes")),
        bidders=bidders,
        boq_items=[],
    )


def _safe_str(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value).strip() or None


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value)
    return parsed.date()


def import_workbook(path: Path, *, dry_run: bool = False) -> ImportResult:
    sheets = load_workbook(path)
    if "Tenders_Master" not in sheets:
        raise ValidationError("Excel must contain a 'Tenders_Master' sheet")
    master_df = sheets["Tenders_Master"]
    bidders_df = sheets.get("Bidders_Detail")

    errors = validate_columns(master_df)
    if errors:
        return ImportResult(total_rows=len(master_df), imported=0, skipped=0, errors=errors)

    db: Session = SessionLocal()
    imported = 0
    skipped = 0
    err_list: list[str] = []
    try:
        service = TenderService(db)
        for idx, row in master_df.iterrows():
            try:
                payload = _row_to_tender_create(db, row, bidders_df)
                if not dry_run:
                    service.create(payload)
                imported += 1
            except (ValidationError, KeyError, ValueError) as exc:
                err_list.append(f"row {idx}: {exc}")
                skipped += 1
        if dry_run:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()

    return ImportResult(
        total_rows=len(master_df),
        imported=imported,
        skipped=skipped,
        errors=err_list,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bulk-import tenders from Excel")
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    configure_logging()
    result = import_workbook(args.path, dry_run=args.dry_run)

    print(f"Total rows : {result.total_rows}")
    print(f"Imported   : {result.imported}")
    print(f"Skipped    : {result.skipped}")
    if result.errors:
        print("Errors:")
        for err in result.errors:
            print(f"  - {err}")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
