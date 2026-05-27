"""BoQ file upload + confirm endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.core.config import get_settings
from api.core.database import get_db
from api.core.errors import NotFoundError, ValidationError
from api.schemas.boq_import import (
    BoqImportConfirmRequest,
    BoqImportConfirmResponse,
    BoqImportPreviewResponse,
    BoqTypeLiteral,
    StagedBoqItemPayload,
)
from api.services.boq_importer import (
    VALID_BOQ_TYPES,
    BoqImporter,
    StagedBoqItem,
)
from api.services.claude_extractor import ClaudeExtractor

router = APIRouter(prefix="/tenders/{tender_id}/boq", tags=["boq-import"])


def _make_importer(db: Session) -> BoqImporter:
    settings = get_settings()
    uploads_root = Path("uploads")
    claude = None
    if settings.anthropic_api_key:
        try:
            claude = ClaudeExtractor(settings)
        except Exception:  # pragma: no cover — defensive
            claude = None
    return BoqImporter(db, claude_extractor=claude, uploads_root=uploads_root)


@router.post(
    "/upload",
    response_model=BoqImportPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a BoQ file (Excel/CSV/PDF) and stage items for review",
)
async def upload_boq(
    tender_id: UUID,
    file: UploadFile = File(...),
    boq_type: BoqTypeLiteral = Form(...),
    source_competitor_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
) -> BoqImportPreviewResponse:
    if boq_type not in VALID_BOQ_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"boq_type must be one of {VALID_BOQ_TYPES}",
        )

    file_bytes = await file.read()
    importer = _make_importer(db)
    try:
        preview = importer.import_file(
            tender_id=tender_id,
            file_bytes=file_bytes,
            filename=file.filename or "uploaded",
            mime_type=file.content_type,
            boq_type=boq_type,
            source_competitor_id=source_competitor_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return BoqImportPreviewResponse(
        tender_id=preview.tender_id,
        boq_type=preview.boq_type,
        source_file_id=preview.source_file_id,
        source_competitor_id=preview.source_competitor_id,
        parser=preview.parser,
        total_items=preview.total_items,
        items_needing_review=preview.items_needing_review,
        items=[
            StagedBoqItemPayload(
                sequence_number=i.sequence_number,
                description=i.description,
                unit=i.unit,
                quantity=i.quantity,
                unit_price=i.unit_price,
                total_price=i.total_price,
                master_item_id=i.master_item_id,
                master_item_code=i.master_item_code,
                matching_confidence=i.matching_confidence,
                matching_method=i.matching_method,
                requires_manual_review=i.requires_manual_review,
            )
            for i in preview.items
        ],
        warnings=preview.warnings,
    )


@router.post(
    "/confirm",
    response_model=BoqImportConfirmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Persist reviewed BoQ items to the correct table",
)
def confirm_boq(
    tender_id: UUID,
    payload: BoqImportConfirmRequest,
    db: Session = Depends(get_db),
) -> BoqImportConfirmResponse:
    importer = _make_importer(db)
    items = [
        StagedBoqItem(
            sequence_number=item.sequence_number,
            description=item.description,
            unit=item.unit,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            master_item_id=item.master_item_id,
            master_item_code=item.master_item_code,
            matching_confidence=item.matching_confidence,
            matching_method=item.matching_method,
            requires_manual_review=item.requires_manual_review,
        )
        for item in payload.items
    ]
    try:
        count = importer.confirm(
            tender_id=tender_id,
            boq_type=payload.boq_type,
            items=items,
            source_file_id=payload.source_file_id,
            source_competitor_id=payload.source_competitor_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return BoqImportConfirmResponse(
        tender_id=tender_id,
        boq_type=payload.boq_type,
        items_committed=count,
    )
