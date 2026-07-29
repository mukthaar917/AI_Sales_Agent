import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import (
    create_customer,
    get_customer_by_id,
    list_customers,
    soft_delete_customer,
    update_customer,
)


router = APIRouter()


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_endpoint(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerResponse:
    customer = create_customer(
        db=db,
        organization_id=current_user.organization_id,
        customer_data=customer_data,
    )

    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=CustomerListResponse,
    status_code=status.HTTP_200_OK,
)
def list_customers_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(
        default=None,
        max_length=255,
    ),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerListResponse:
    customers, total = list_customers(
        db=db,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        include_inactive=include_inactive,
    )

    return CustomerListResponse(
        items=[
            CustomerResponse.model_validate(customer)
            for customer in customers
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_endpoint(
    customer_id: uuid.UUID,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerResponse:
    customer = get_customer_by_id(
        db=db,
        organization_id=current_user.organization_id,
        customer_id=customer_id,
        include_inactive=include_inactive,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
def update_customer_endpoint(
    customer_id: uuid.UUID,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerResponse:
    customer = get_customer_by_id(
        db=db,
        organization_id=current_user.organization_id,
        customer_id=customer_id,
        include_inactive=True,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    updated_customer = update_customer(
        db=db,
        customer=customer,
        customer_data=customer_data,
    )

    return CustomerResponse.model_validate(updated_customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer_endpoint(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    customer = get_customer_by_id(
        db=db,
        organization_id=current_user.organization_id,
        customer_id=customer_id,
        include_inactive=True,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    soft_delete_customer(
        db=db,
        customer=customer,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )