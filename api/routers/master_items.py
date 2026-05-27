"""Master items CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import MasterItem, MasterItemSynonym
from api.schemas.master_item import (
    MasterItemCreate,
    MasterItemOut,
    MasterItemSynonymCreate,
    MasterItemSynonymOut,
)

router = APIRouter(prefix="/master-items", tags=["master-items"])


@router.post("", response_model=MasterItemOut, status_code=status.HTTP_201_CREATED)
def create_master_item(data: MasterItemCreate, db: Session = Depends(get_db)) -> MasterItemOut:
    existing = db.execute(
        select(MasterItem).where(MasterItem.code == data.code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"code {data.code} already exists")

    mi = MasterItem(
        code=data.code,
        name_ar=data.name_ar,
        name_en=data.name_en,
        description_ar=data.description_ar,
        description_en=data.description_en,
        category_id=data.category_id,
        parent_item_id=data.parent_item_id,
        default_unit=data.default_unit,
        alternative_units=data.alternative_units,
        specifications=data.specifications,
        confidence_baseline=data.confidence_baseline,
    )
    db.add(mi)
    db.commit()
    db.refresh(mi)
    return MasterItemOut.model_validate(mi)


@router.get("", response_model=list[MasterItemOut])
def list_master_items(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[MasterItemOut]:
    stmt = select(MasterItem).order_by(MasterItem.code).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [MasterItemOut.model_validate(r) for r in rows]


@router.get("/{master_item_id}", response_model=MasterItemOut)
def get_master_item(master_item_id: UUID, db: Session = Depends(get_db)) -> MasterItemOut:
    mi = db.get(MasterItem, master_item_id)
    if mi is None:
        raise HTTPException(status_code=404, detail="master item not found")
    return MasterItemOut.model_validate(mi)


@router.post(
    "/synonyms", response_model=MasterItemSynonymOut, status_code=status.HTTP_201_CREATED
)
def add_synonym(
    data: MasterItemSynonymCreate, db: Session = Depends(get_db)
) -> MasterItemSynonymOut:
    if db.get(MasterItem, data.master_item_id) is None:
        raise HTTPException(status_code=404, detail="master item not found")
    syn = MasterItemSynonym(
        master_item_id=data.master_item_id,
        synonym_text=data.synonym_text,
        source=data.source,
    )
    db.add(syn)
    db.commit()
    db.refresh(syn)
    return MasterItemSynonymOut.model_validate(syn)
