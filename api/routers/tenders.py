"""Tender CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.core.errors import NotFoundError, ValidationError
from api.schemas.tender import BoqItemIn, TenderCreate, TenderOut, TenderUpdate
from api.services.tender_service import TenderService

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.post("", response_model=TenderOut, status_code=status.HTTP_201_CREATED)
def create_tender(data: TenderCreate, db: Session = Depends(get_db)) -> TenderOut:
    service = TenderService(db)
    try:
        tender = service.create(data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TenderOut.model_validate(tender)


@router.get("", response_model=list[TenderOut])
def list_tenders(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    government_entity_id: UUID | None = None,
    sector_id: UUID | None = None,
    rawasi_participated: bool | None = None,
    db: Session = Depends(get_db),
) -> list[TenderOut]:
    service = TenderService(db)
    tenders = service.list(
        skip=skip,
        limit=limit,
        government_entity_id=government_entity_id,
        sector_id=sector_id,
        rawasi_participated=rawasi_participated,
    )
    return [TenderOut.model_validate(t) for t in tenders]


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: UUID, db: Session = Depends(get_db)) -> TenderOut:
    service = TenderService(db)
    try:
        tender = service.get(tender_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TenderOut.model_validate(tender)


@router.patch("/{tender_id}", response_model=TenderOut)
def update_tender(
    tender_id: UUID, data: TenderUpdate, db: Session = Depends(get_db)
) -> TenderOut:
    service = TenderService(db)
    try:
        tender = service.update(tender_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TenderOut.model_validate(tender)


@router.post(
    "/{tender_id}/boq-items",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_boq_items(
    tender_id: UUID, items: list[BoqItemIn], db: Session = Depends(get_db)
) -> None:
    service = TenderService(db)
    try:
        service.add_boq_items(tender_id, items)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{tender_id}/anomaly-check")
def anomaly_check(tender_id: UUID, db: Session = Depends(get_db)) -> dict:
    service = TenderService(db)
    try:
        tender = service.get(tender_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    warning = service.check_anomaly(tender)
    return {"is_anomalous": warning is not None, "warning": warning}
