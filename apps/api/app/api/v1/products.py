import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import (
    create_product,
    get_product_by_id,
    list_products,
    soft_delete_product,
    update_product,
)


router = APIRouter()


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_endpoint(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    try:
        product = create_product(
            db=db,
            organization_id=current_user.organization_id,
            product_data=product_data,
        )
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        ) from exc

    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
)
def list_products_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(
        default=None,
        max_length=255,
    ),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductListResponse:
    products, total = list_products(
        db=db,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        include_inactive=include_inactive,
    )

    return ProductListResponse(
        items=[
            ProductResponse.model_validate(product)
            for product in products
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get_product_endpoint(
    product_id: uuid.UUID,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    product = get_product_by_id(
        db=db,
        organization_id=current_user.organization_id,
        product_id=product_id,
        include_inactive=include_inactive,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def update_product_endpoint(
    product_id: uuid.UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    product = get_product_by_id(
        db=db,
        organization_id=current_user.organization_id,
        product_id=product_id,
        include_inactive=True,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    try:
        updated_product = update_product(
            db=db,
            product=product,
            product_data=product_data,
        )
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        ) from exc

    return ProductResponse.model_validate(updated_product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_endpoint(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    product = get_product_by_id(
        db=db,
        organization_id=current_user.organization_id,
        product_id=product_id,
        include_inactive=True,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    soft_delete_product(
        db=db,
        product=product,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )