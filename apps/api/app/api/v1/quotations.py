import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.quotation import QuotationStatus
from app.models.user import User
from app.schemas.quotation import (
    QuotationCreate,
    QuotationListResponse,
    QuotationResponse,
    QuotationUpdate,
)
from app.services.quotation_pdf_service import generate_quotation_pdf
from app.services.quotation_service import (
    create_quotation,
    delete_quotation,
    get_quotation_by_id,
    list_quotations,
    update_quotation,
)


router = APIRouter()


@router.post(
    "",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation_endpoint(
    quotation_in: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationResponse:
    try:
        quotation = create_quotation(
            db=db,
            quotation_in=quotation_in,
            current_user=current_user,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quotation was created but could not be loaded",
        )

    return quotation


@router.get(
    "",
    response_model=QuotationListResponse,
)
def list_quotations_endpoint(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
    ),
    quotation_status: QuotationStatus | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationListResponse:
    quotations, total = list_quotations(
        db=db,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        status=quotation_status,
    )

    return QuotationListResponse(
        items=quotations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{quotation_id}/pdf",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "content": {
                "application/pdf": {},
            },
            "description": "Quotation PDF",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Quotation not found",
        },
    },
)
def download_quotation_pdf_endpoint(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation_id,
        organization_id=current_user.organization_id,
    )

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found",
        )

    try:
        pdf_bytes = generate_quotation_pdf(
            quotation=quotation,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate quotation PDF",
        ) from exc

    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated quotation PDF is empty",
        )

    filename = f"{quotation.quotation_number}.pdf"

    return Response(
        content=pdf_bytes,
        status_code=status.HTTP_200_OK,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get(
    "/{quotation_id}",
    response_model=QuotationResponse,
)
def get_quotation_endpoint(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationResponse:
    quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation_id,
        organization_id=current_user.organization_id,
    )

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found",
        )

    return quotation


@router.put(
    "/{quotation_id}",
    response_model=QuotationResponse,
)
def update_quotation_endpoint(
    quotation_id: uuid.UUID,
    quotation_in: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationResponse:
    quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation_id,
        organization_id=current_user.organization_id,
    )

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found",
        )

    try:
        updated_quotation = update_quotation(
            db=db,
            quotation=quotation,
            quotation_in=quotation_in,
            current_user=current_user,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if updated_quotation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quotation was updated but could not be loaded",
        )

    return updated_quotation


@router.delete(
    "/{quotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_quotation_endpoint(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation_id,
        organization_id=current_user.organization_id,
    )

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found",
        )

    delete_quotation(
        db=db,
        quotation=quotation,
    )