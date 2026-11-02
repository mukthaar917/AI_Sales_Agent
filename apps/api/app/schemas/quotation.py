import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.quotation import QuotationStatus


class QuotationItemBase(BaseModel):
    product_id: uuid.UUID | None = None

    description: str = Field(
        min_length=1,
    )

    quantity: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    unit: str = Field(
        default="unit",
        min_length=1,
        max_length=50,
    )

    unit_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    discount_rate: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    tax_rate: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    sort_order: int = Field(
        default=1,
        ge=1,
    )

    @field_validator("description", "unit")
    @classmethod
    def strip_required_item_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty")

        return value


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemUpdate(BaseModel):
    product_id: uuid.UUID | None = None

    description: str | None = Field(
        default=None,
        min_length=1,
    )

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    unit_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    discount_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    tax_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    sort_order: int | None = Field(
        default=None,
        ge=1,
    )

    @field_validator("description", "unit")
    @classmethod
    def strip_optional_item_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty")

        return value


class QuotationItemResponse(QuotationItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quotation_id: uuid.UUID

    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal

    created_at: datetime
    updated_at: datetime


class QuotationBase(BaseModel):
    customer_id: uuid.UUID

    issue_date: date
    expiry_date: date

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )

    notes: str | None = None
    terms: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()

        if len(value) != 3 or not value.isalpha():
            raise ValueError(
                "Currency must be a three-letter alphabetic code"
            )

        return value

    @field_validator("notes", "terms")
    @classmethod
    def strip_optional_quotation_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_expiry_date(self) -> "QuotationBase":
        if self.expiry_date < self.issue_date:
            raise ValueError(
                "Expiry date cannot be earlier than issue date"
            )

        return self


class QuotationCreate(QuotationBase):
    items: list[QuotationItemCreate] = Field(
        min_length=1,
    )


class QuotationUpdate(BaseModel):
    status: QuotationStatus | None = None

    customer_id: uuid.UUID | None = None

    issue_date: date | None = None
    expiry_date: date | None = None

    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    notes: str | None = None
    terms: str | None = None

    items: list[QuotationItemCreate] | None = Field(
        default=None,
        min_length=1,
    )

    @field_validator("currency")
    @classmethod
    def normalize_optional_currency(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip().upper()

        if len(value) != 3 or not value.isalpha():
            raise ValueError(
                "Currency must be a three-letter alphabetic code"
            )

        return value

    @field_validator("notes", "terms")
    @classmethod
    def strip_optional_update_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_update_dates(self) -> "QuotationUpdate":
        if (
            self.issue_date is not None
            and self.expiry_date is not None
            and self.expiry_date < self.issue_date
        ):
            raise ValueError(
                "Expiry date cannot be earlier than issue date"
            )

        return self


class QuotationResponse(QuotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID

    quotation_number: str
    status: QuotationStatus

    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal

    items: list[QuotationItemResponse]

    created_at: datetime
    updated_at: datetime


class QuotationListResponse(BaseModel):
    items: list[QuotationResponse]
    total: int
    page: int
    page_size: int