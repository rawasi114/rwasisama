"""Tender CRUD service with built-in validation and statistical anomaly check."""

from __future__ import annotations

from datetime import date
from statistics import mean
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.errors import NotFoundError, ValidationError
from api.models import (
    Competitor,
    GovernmentEntity,
    Tender,
    TenderBidder,
    TenderBoqItem,
)
from api.schemas.tender import BoqItemIn, TenderBidderIn, TenderCreate, TenderUpdate

ANOMALY_DEVIATION_RATIO = 0.80


class TenderService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: TenderCreate) -> Tender:
        self._validate_create(data)

        if data.etimad_tender_id:
            existing = self.db.execute(
                select(Tender).where(Tender.etimad_tender_id == data.etimad_tender_id)
            ).scalar_one_or_none()
            if existing:
                raise ValidationError(
                    f"tender with etimad_tender_id={data.etimad_tender_id} already exists"
                )

        if self.db.get(GovernmentEntity, data.government_entity_id) is None:
            raise ValidationError("government_entity_id is not valid")
        if self.db.get(Competitor, data.awarded_to_competitor_id) is None:
            raise ValidationError("awarded_to_competitor_id is not valid")

        tender = Tender(
            etimad_tender_id=data.etimad_tender_id,
            internal_reference=data.internal_reference,
            title_ar=data.title_ar,
            title_en=data.title_en,
            description_ar=data.description_ar,
            government_entity_id=data.government_entity_id,
            sub_entity_name=data.sub_entity_name,
            region_id=data.region_id,
            city_id=data.city_id,
            project_site_details=data.project_site_details,
            primary_sector_id=data.primary_sector_id,
            secondary_sectors=[str(s) for s in (data.secondary_sectors or [])] or None,
            required_classification_grade=data.required_classification_grade,
            requires_pre_qualification=data.requires_pre_qualification,
            publication_date=data.publication_date,
            submission_deadline=data.submission_deadline,
            bid_opening_date=data.bid_opening_date,
            award_date=data.award_date,
            execution_duration_days=data.execution_duration_days,
            bid_bond_value=data.bid_bond_value,
            award_value=data.award_value,
            awarded_to_competitor_id=data.awarded_to_competitor_id,
            total_bidders_count=data.total_bidders_count,
            rawasi_participated=data.rawasi_participated,
            notes=data.notes,
        )
        self.db.add(tender)
        self.db.flush()

        for item in data.boq_items:
            self.db.add(self._make_boq_item(tender.id, item))

        for bidder in data.bidders:
            self.db.add(self._make_bidder(tender.id, bidder))

        if data.boq_items:
            tender.has_full_boq = True

        self.db.commit()
        self.db.refresh(tender)
        return tender

    def get(self, tender_id: UUID) -> Tender:
        tender = self.db.get(Tender, tender_id)
        if tender is None:
            raise NotFoundError(f"tender {tender_id} not found")
        return tender

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        government_entity_id: UUID | None = None,
        sector_id: UUID | None = None,
        rawasi_participated: bool | None = None,
    ) -> list[Tender]:
        stmt = select(Tender).order_by(Tender.award_date.desc()).offset(skip).limit(limit)
        if government_entity_id:
            stmt = stmt.where(Tender.government_entity_id == government_entity_id)
        if sector_id:
            stmt = stmt.where(Tender.primary_sector_id == sector_id)
        if rawasi_participated is not None:
            stmt = stmt.where(Tender.rawasi_participated == rawasi_participated)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, tender_id: UUID, data: TenderUpdate) -> Tender:
        tender = self.get(tender_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tender, key, value)
        self.db.commit()
        self.db.refresh(tender)
        return tender

    def add_boq_items(self, tender_id: UUID, items: list[BoqItemIn]) -> None:
        tender = self.get(tender_id)
        for item in items:
            self.db.add(self._make_boq_item(tender.id, item))
        if items:
            tender.has_full_boq = True
        self.db.commit()

    def check_anomaly(self, tender: Tender) -> str | None:
        peers = self.db.execute(
            select(Tender.award_value).where(
                Tender.primary_sector_id == tender.primary_sector_id,
                Tender.id != tender.id,
                Tender.award_date >= date(tender.award_date.year - 2, 1, 1),
            )
        ).scalars().all()
        if len(peers) < 5:
            return None
        peer_values = [float(p) for p in peers]
        mu = mean(peer_values)
        if mu <= 0:
            return None
        deviation = abs(float(tender.award_value) - mu) / mu
        if deviation >= ANOMALY_DEVIATION_RATIO:
            return (
                f"Award value deviates {deviation:.0%} from the sector's "
                f"two-year mean ({mu:,.0f} SAR). Verify before saving."
            )
        return None

    def _validate_create(self, data: TenderCreate) -> None:
        if data.publication_date and data.publication_date > data.award_date:
            raise ValidationError("publication_date cannot be after award_date")
        if data.submission_deadline and data.publication_date:
            if data.submission_deadline < data.publication_date:
                raise ValidationError("submission_deadline cannot be before publication_date")
        if data.rawasi_participated and data.total_bidders_count is not None:
            for bidder in data.bidders:
                if (
                    bidder.bid_rank is not None
                    and bidder.bid_rank > data.total_bidders_count
                ):
                    raise ValidationError(
                        "bidder rank cannot exceed total_bidders_count"
                    )

    @staticmethod
    def _make_boq_item(tender_id: UUID, item: BoqItemIn) -> TenderBoqItem:
        return TenderBoqItem(
            tender_id=tender_id,
            sequence_number=item.sequence_number,
            original_description=item.original_description,
            original_unit=item.original_unit,
            quantity=item.quantity,
            unit_estimated_price=item.unit_estimated_price,
            item_category=item.item_category,
            notes=item.notes,
        )

    @staticmethod
    def _make_bidder(tender_id: UUID, bidder: TenderBidderIn) -> TenderBidder:
        return TenderBidder(
            tender_id=tender_id,
            competitor_id=bidder.competitor_id,
            bidder_name_as_appeared=bidder.bidder_name_as_appeared,
            bid_amount=bidder.bid_amount,
            bid_rank=bidder.bid_rank,
            was_qualified=bidder.was_qualified,
            rejection_reason=bidder.rejection_reason,
            notes=bidder.notes,
        )
