import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class CustomerBase(BaseModel):
    company_name: str = Field(
        min_length=1,
        max_length=255,
    )
    contact_name: str | None = Field(
        default=None,
        max_length=255,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )
    website: HttpUrl | None = None
    address: str | None = None
    city: str | None = Field(
        default=None,
        max_length=100,
    )
    state: str | None = Field(
        default=None,
        max_length=100,
    )
    country: str | None = Field(
        default=None,
        max_length=100,
    )
    postal_code: str | None = Field(
        default=None,
        max_length=30,
    )
    tax_number: str | None = Field(
        default=None,
        max_length=100,
    )
    notes: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    company_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    contact_name: str | None = Field(
        default=None,
        max_length=255,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=50,
    )
    website: HttpUrl | None = None
    address: str | None = None
    city: str | None = Field(
        default=None,
        max_length=100,
    )
    state: str | None = Field(
        default=None,
        max_length=100,
    )
    country: str | None = Field(
        default=None,
        max_length=100,
    )
    postal_code: str | None = Field(
        default=None,
        max_length=30,
    )
    tax_number: str | None = Field(
        default=None,
        max_length=100,
    )
    notes: str | None = None
    is_active: bool | None = None


class CustomerResponse(CustomerBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int