"""Reviewable quotation preview service."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.user import User
from app.services.quotation_service import (
    calculate_line,
    find_product_by_name_for_organization,
)


class QuotationPreviewError(RuntimeError):
    """Raised when a quotation preview cannot be prepared."""


@dataclass
class QuotationPreviewResult:
    """Reviewable quotation preview values."""

    customer_id: str
    customer_name: str
    customer_email: str | None

    product_id: str
    product_name: str

    quantity: Decimal
    unit: str
    unit_price: Decimal
    currency: str
    tax_rate: Decimal

    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class QuotationPreviewService:
    """Prepare a quotation preview from extracted RFQ requirements."""

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def prepare(
        self,
        *,
        current_user: User,
        sender_email: str,
        product_name: str,
        quantity: int,
    ) -> QuotationPreviewResult:
        normalized_sender = sender_email.strip().lower()
        normalized_product = product_name.strip()

        if not normalized_sender:
            raise QuotationPreviewError(
                "Customer email is required."
            )

        if not normalized_product:
            raise QuotationPreviewError(
                "Extracted product is required."
            )

        if quantity < 1:
            raise QuotationPreviewError(
                "Extracted quantity must be at least 1."
            )

        customer = self.db.scalar(
            select(Customer).where(
                Customer.organization_id
                == current_user.organization_id,
                Customer.is_active.is_(True),
                func.lower(Customer.email)
                == normalized_sender,
            )
        )

        if customer is None:
            raise QuotationPreviewError(
                "No active customer matches the RFQ sender email."
            )

        product = find_product_by_name_for_organization(
            db=self.db,
            product_name=normalized_product,
            organization_id=current_user.organization_id,
        )

        if product is None:
            raise QuotationPreviewError(
                "No active product matches the extracted requirement."
            )

        quantity_decimal = Decimal(
            str(quantity)
        )

        line = calculate_line(
            quantity=quantity_decimal,
            unit_price=product.unit_price,
            discount_rate=Decimal("0.00"),
            tax_rate=product.tax_rate,
        )

        return QuotationPreviewResult(
            customer_id=str(customer.id),
            customer_name=customer.company_name,
            customer_email=customer.email,
            product_id=str(product.id),
            product_name=product.name,
            quantity=quantity_decimal,
            unit=product.unit,
            unit_price=product.unit_price,
            currency=product.currency,
            tax_rate=product.tax_rate,
            subtotal=line["subtotal"],
            tax_amount=line["tax_amount"],
            total_amount=line["line_total"],
        )