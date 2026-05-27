"""Run the weekly data-quality audit.

Produces a report covering:
- Tenders missing BoQs or award announcements.
- BoQ items below the manual-review threshold.
- Statistical outliers in award values.
- Unmatched bidders (bidder rows without a competitor link).

Usage:
    python -m scripts.data_quality_check [--json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.database import SessionLocal
from api.core.logging import configure_logging, get_logger
from api.models import Sector, Tender, TenderBidder, TenderBoqItem

LOG = get_logger(__name__)


@dataclass
class QualityReport:
    period_start: date
    period_end: date
    total_tenders: int
    full_data_tenders: int
    pending_review_tenders: list[dict] = field(default_factory=list)
    low_confidence_items: int = 0
    unmatched_bidders: int = 0
    outlier_tenders: list[dict] = field(default_factory=list)
    sector_distribution: dict[str, int] = field(default_factory=dict)

    @property
    def full_data_pct(self) -> float:
        if self.total_tenders == 0:
            return 0.0
        return self.full_data_tenders / self.total_tenders


def compute_report(db: Session, *, days_back: int = 7) -> QualityReport:
    period_end = date.today()
    period_start = period_end - timedelta(days=days_back)

    tenders = db.execute(
        select(Tender).where(
            Tender.created_at >= period_start,
        )
    ).scalars().all()

    full_count = sum(
        1
        for t in tenders
        if t.has_full_boq and t.has_award_announcement
    )

    pending_review = [
        {
            "id": str(t.id),
            "title": t.title_ar,
            "etimad_id": t.etimad_tender_id,
        }
        for t in tenders
        if not t.has_full_boq or not t.has_award_announcement
    ]

    low_conf = db.execute(
        select(func.count(TenderBoqItem.id)).where(
            TenderBoqItem.matching_confidence < 0.7,
            TenderBoqItem.matching_confidence.is_not(None),
        )
    ).scalar() or 0

    unmatched = db.execute(
        select(func.count(TenderBidder.id)).where(
            TenderBidder.competitor_id.is_(None)
        )
    ).scalar() or 0

    outlier = _detect_outliers(db, tenders)

    sector_dist: dict[str, int] = {}
    for t in tenders:
        if t.primary_sector_id is None:
            continue
        sector = db.get(Sector, t.primary_sector_id)
        if sector:
            sector_dist[sector.name_ar] = sector_dist.get(sector.name_ar, 0) + 1

    return QualityReport(
        period_start=period_start,
        period_end=period_end,
        total_tenders=len(tenders),
        full_data_tenders=full_count,
        pending_review_tenders=pending_review,
        low_confidence_items=low_conf,
        unmatched_bidders=unmatched,
        outlier_tenders=outlier,
        sector_distribution=sector_dist,
    )


def _detect_outliers(db: Session, tenders: list[Tender]) -> list[dict]:
    """Flag tenders whose value deviates >= 1.5 SD from sector mean."""
    by_sector: dict[Any, list[float]] = {}
    for t in tenders:
        if t.primary_sector_id is None:
            continue
        by_sector.setdefault(t.primary_sector_id, []).append(float(t.award_value))

    outliers: list[dict] = []
    for t in tenders:
        if t.primary_sector_id is None:
            continue
        values = by_sector.get(t.primary_sector_id, [])
        if len(values) < 5:
            continue
        mu = statistics.mean(values)
        sd = statistics.pstdev(values) or 1.0
        deviation = abs(float(t.award_value) - mu) / sd
        if deviation >= 1.5:
            outliers.append(
                {
                    "tender_id": str(t.id),
                    "title": t.title_ar,
                    "award_value": float(t.award_value),
                    "sector_mean": mu,
                    "deviation_sd": round(deviation, 2),
                }
            )
    return outliers


def print_report_text(report: QualityReport) -> None:
    print(f"{'═' * 60}")
    print("تقرير جودة البيانات")
    print(f"الفترة: {report.period_start} → {report.period_end}")
    print(f"{'═' * 60}")
    print(f"إجمالي الترسيات: {report.total_tenders}")
    print(
        f"الترسيات بالبيانات الكاملة: {report.full_data_tenders}"
        f" ({report.full_data_pct:.0%})"
    )
    print(f"بنود بثقة منخفضة: {report.low_confidence_items}")
    print(f"متنافسون غير مربوطين: {report.unmatched_bidders}")
    if report.outlier_tenders:
        print()
        print(f"⚠️ ترسيات شاذة ({len(report.outlier_tenders)}):")
        for o in report.outlier_tenders[:10]:
            print(f"  • {o['title']} — {o['award_value']:,.0f} (انحراف {o['deviation_sd']}σ)")
    if report.sector_distribution:
        print()
        print("📊 توزيع القطاعات:")
        for name, count in sorted(
            report.sector_distribution.items(), key=lambda x: -x[1]
        ):
            print(f"  • {name}: {count}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    configure_logging()
    db = SessionLocal()
    try:
        report = compute_report(db, days_back=args.days)
    finally:
        db.close()

    if args.json:
        print(
            json.dumps(asdict(report), default=str, ensure_ascii=False, indent=2)
        )
    else:
        print_report_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
