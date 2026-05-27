"""Competitor profile engine — engine #3."""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.errors import InsufficientDataError, NotFoundError
from api.models import Competitor, CompetitorProfile, Tender, TenderBidder
from api.schemas.analytics import CompetitorBidPrediction, CompetitorProfileOut
from api.utils.stats import clamp


class CompetitorProfileEngine:
    """Engine #3: builds and queries competitor profiles."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_profile(
        self, competitor_id: UUID, period_months: int = 24
    ) -> CompetitorProfileOut:
        competitor = self.db.get(Competitor, competitor_id)
        if competitor is None:
            raise NotFoundError(f"competitor {competitor_id} not found")

        cutoff = datetime.utcnow().date() - timedelta(days=period_months * 30)

        appearances = self.db.execute(
            select(Tender, TenderBidder)
            .join(TenderBidder, TenderBidder.tender_id == Tender.id)
            .where(
                TenderBidder.competitor_id == competitor_id,
                Tender.award_date >= cutoff,
            )
        ).all()

        wins_data = self.db.execute(
            select(Tender)
            .where(
                Tender.awarded_to_competitor_id == competitor_id,
                Tender.award_date >= cutoff,
            )
        ).scalars().all()

        appearance_count = len(appearances)
        win_count = len(wins_data)
        if appearance_count == 0 and win_count == 0:
            raise InsufficientDataError(
                f"no observations found for competitor {competitor_id} in last {period_months}m"
            )

        won_values = [float(t.award_value) for t in wins_data]
        avg_award = statistics.mean(won_values) if won_values else None
        median_award = statistics.median(won_values) if won_values else None

        sector_dist = self._distribution(wins_data, lambda t: str(t.primary_sector_id))
        region_dist = self._distribution(wins_data, lambda t: str(t.region_id))
        entity_dist = self._distribution(wins_data, lambda t: str(t.government_entity_id))

        win_rate = (win_count / appearance_count) if appearance_count else 0.0
        threat = self._threat_score(win_count, appearance_count, avg_award or 0.0)

        profile = CompetitorProfileOut(
            competitor_id=competitor_id,
            analysis_period_months=period_months,
            total_appearances=appearance_count,
            total_wins=win_count,
            win_rate=win_rate,
            avg_award_value=avg_award,
            median_award_value=median_award,
            avg_discount_vs_reference_pct=None,
            sector_distribution=sector_dist,
            region_distribution=region_dist,
            entity_distribution=entity_dist,
            threat_score=threat,
            predicted_categories=[k for k, v in sector_dist.items() if v >= 0.15],
        )

        self._persist(profile)
        return profile

    def predict_bid(
        self, competitor_id: UUID, tender: Tender, reference_value: float
    ) -> CompetitorBidPrediction:
        profile = self.get_persisted_profile(competitor_id, period_months=24)
        if profile is None:
            return CompetitorBidPrediction(
                competitor_id=competitor_id,
                entry_probability=0.3,
                estimated_bid_range=None,
                confidence=0.2,
            )

        sector_share = profile.sector_distribution.get(
            str(tender.primary_sector_id), 0.0
        )
        region_share = profile.region_distribution.get(str(tender.region_id), 0.0)
        entity_share = profile.entity_distribution.get(
            str(tender.government_entity_id), 0.0
        )
        entry = clamp(
            0.3 + 0.4 * sector_share + 0.2 * region_share + 0.2 * entity_share,
            0.0,
            1.0,
        )

        if reference_value > 0:
            low = reference_value * 0.85
            high = reference_value * 1.05
            bid_range: tuple[float, float] | None = (low, high)
        else:
            bid_range = None

        return CompetitorBidPrediction(
            competitor_id=competitor_id,
            entry_probability=entry,
            estimated_bid_range=bid_range,
            confidence=clamp(profile.total_wins / 20, 0.1, 0.9),
        )

    def get_persisted_profile(
        self, competitor_id: UUID, period_months: int = 24
    ) -> CompetitorProfileOut | None:
        row = self.db.execute(
            select(CompetitorProfile).where(
                CompetitorProfile.competitor_id == competitor_id,
                CompetitorProfile.analysis_period_months == period_months,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return CompetitorProfileOut(
            competitor_id=row.competitor_id,
            analysis_period_months=row.analysis_period_months,
            total_appearances=row.total_appearances or 0,
            total_wins=row.total_wins or 0,
            win_rate=float(row.win_rate or 0),
            avg_award_value=float(row.avg_award_value) if row.avg_award_value else None,
            median_award_value=float(row.median_award_value)
            if row.median_award_value
            else None,
            avg_discount_vs_reference_pct=float(row.avg_discount_vs_reference_pct)
            if row.avg_discount_vs_reference_pct is not None
            else None,
            sector_distribution=row.sector_distribution or {},
            region_distribution=row.region_distribution or {},
            entity_distribution=row.entity_distribution or {},
            threat_score=row.threat_score,
            predicted_categories=row.predicted_appearance_categories or [],
        )

    def _persist(self, profile: CompetitorProfileOut) -> None:
        row = self.db.execute(
            select(CompetitorProfile).where(
                CompetitorProfile.competitor_id == profile.competitor_id,
                CompetitorProfile.analysis_period_months
                == profile.analysis_period_months,
            )
        ).scalar_one_or_none()

        if row is None:
            row = CompetitorProfile(
                competitor_id=profile.competitor_id,
                analysis_period_months=profile.analysis_period_months,
                last_calculated_at=datetime.utcnow(),
            )
            self.db.add(row)

        row.last_calculated_at = datetime.utcnow()
        row.total_appearances = profile.total_appearances
        row.total_wins = profile.total_wins
        row.win_rate = profile.win_rate * 100 if profile.win_rate <= 1 else profile.win_rate
        row.avg_award_value = profile.avg_award_value
        row.median_award_value = profile.median_award_value
        row.sector_distribution = profile.sector_distribution
        row.region_distribution = profile.region_distribution
        row.entity_distribution = profile.entity_distribution
        row.threat_score = profile.threat_score
        row.predicted_appearance_categories = profile.predicted_categories
        self.db.flush()

    @staticmethod
    def _distribution(rows, key) -> dict[str, float]:
        counter: Counter = Counter()
        for row in rows:
            k = key(row)
            if k and k != "None":
                counter[k] += 1
        total = sum(counter.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in counter.most_common()}

    @staticmethod
    def _threat_score(wins: int, appearances: int, avg_award: float) -> int:
        activity = clamp(appearances / 20, 0.0, 1.0)
        success = clamp((wins / appearances) if appearances else 0, 0.0, 1.0)
        scale = clamp(avg_award / 5_000_000, 0.0, 1.0)
        score = 100 * (0.5 * success + 0.3 * activity + 0.2 * scale)
        return int(clamp(score, 1, 100))
