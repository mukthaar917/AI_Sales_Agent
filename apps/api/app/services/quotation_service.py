import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.product import Product
from app.models.quotation import Quotation, QuotationStatus
from app.models.quotation_item import QuotationItem
from app.models.user import User
from app.schemas.quotation import QuotationCreate, QuotationUpdate


MONEY_PLACES = Decimal("0.01")
RATE_DIVISOR = Decimal("100")


ALLOWED_QUOTATION_STATUS_TRANSITIONS: dict[
    QuotationStatus,
    set[QuotationStatus],
] = {
    QuotationStatus.DRAFT: {
        QuotationStatus.REVIEWED,
        QuotationStatus.CANCELLED,
    },
    QuotationStatus.REVIEWED: {
        QuotationStatus.APPROVED,
        QuotationStatus.DRAFT,
        QuotationStatus.CANCELLED,
    },
    QuotationStatus.APPROVED: {
        QuotationStatus.SENT,
        QuotationStatus.REVIEWED,
        QuotationStatus.CANCELLED,
    },
    QuotationStatus.SENT: {
        QuotationStatus.ACCEPTED,
        QuotationStatus.REJECTED,
        QuotationStatus.EXPIRED,
    },
    QuotationStatus.ACCEPTED: set(),
    QuotationStatus.REJECTED: set(),
    QuotationStatus.EXPIRED: set(),
    QuotationStatus.CANCELLED: set(),
}


def validate_quotation_status_transition(
    current_status: QuotationStatus,
    new_status: QuotationStatus,
) -> None:
    """Validate one quotation lifecycle transition."""

    if new_status == current_status:
        return

    allowed_statuses = ALLOWED_QUOTATION_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )

    if new_status not in allowed_statuses:
        raise ValueError(
            "Invalid quotation status transition: "
            f"{current_status.value} -> {new_status.value}"
        )


def round_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""
    return value.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def calculate_line(
    quantity: Decimal,
    unit_price: Decimal,
    discount_rate: Decimal,
    tax_rate: Decimal,
) -> dict[str, Decimal]:
    """Calculate subtotal, discount, tax, and total for one item."""
    subtotal = round_money(
        quantity * unit_price
    )

    discount_amount = round_money(
        subtotal * discount_rate / RATE_DIVISOR
    )

    taxable_amount = round_money(
        subtotal - discount_amount
    )

    tax_amount = round_money(
        taxable_amount * tax_rate / RATE_DIVISOR
    )

    line_total = round_money(
        taxable_amount + tax_amount
    )

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "line_total": line_total,
    }


def calculate_totals(
    items: list[QuotationItem],
) -> dict[str, Decimal]:
    """Calculate quotation totals from quotation items."""
    subtotal = round_money(
        sum(
            (item.subtotal for item in items),
            Decimal("0.00"),
        )
    )

    discount_amount = round_money(
        sum(
            (item.discount_amount for item in items),
            Decimal("0.00"),
        )
    )

    tax_amount = round_money(
        sum(
            (item.tax_amount for item in items),
            Decimal("0.00"),
        )
    )

    total_amount = round_money(
        sum(
            (item.line_total for item in items),
            Decimal("0.00"),
        )
    )

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


def generate_quotation_number(
    db: Session,
    organization_id: uuid.UUID,
) -> str:
    """Generate the next quotation number for an organization."""
    current_year = datetime.utcnow().year
    prefix = f"Q-{current_year}-"

    latest_number = db.scalar(
        select(Quotation.quotation_number)
        .where(
            Quotation.organization_id == organization_id,
            Quotation.quotation_number.like(f"{prefix}%"),
        )
        .order_by(
            Quotation.quotation_number.desc(),
        )
        .limit(1)
    )

    if latest_number is None:
        next_sequence = 1
    else:
        try:
            sequence_text = latest_number.rsplit(
                "-",
                maxsplit=1,
            )[-1]

            next_sequence = int(sequence_text) + 1
        except (TypeError, ValueError):
            next_sequence = 1

    return f"{prefix}{next_sequence:06d}"


def get_customer_for_organization(
    db: Session,
    customer_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Customer | None:
    """Return an active customer belonging to an organization."""
    return db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
    )


def find_product_by_name_for_organization(
    db: Session,
    product_name: str,
    organization_id: uuid.UUID,
) -> Product | None:
    """Find one active organization product by extracted product text."""

    normalized = " ".join(
        product_name.lower().split()
    ).strip()

    if not normalized:
        return None

    search_value = f"%{normalized.rstrip('s')}%"

    return db.scalar(
        select(Product).where(
            Product.organization_id == organization_id,
            Product.is_active.is_(True),
            or_(
                func.lower(Product.name).like(search_value),
                func.lower(Product.description).like(search_value),
                func.lower(Product.sku).like(search_value),
            ),
        )
        .order_by(Product.name.asc())
        .limit(1)
    )


def get_product_for_organization(
    db: Session,
    product_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Product | None:
    """Return an active product belonging to an organization."""
    return db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
            Product.is_active.is_(True),
        )
    )


def validate_product_for_organization(
    db: Session,
    product_id: uuid.UUID | None,
    organization_id: uuid.UUID,
) -> None:
    """Validate an optional quotation item product."""
    if product_id is None:
        return

    product = get_product_for_organization(
        db=db,
        product_id=product_id,
        organization_id=organization_id,
    )

    if product is None:
        raise ValueError(
            "Product not found or does not belong to this organization"
        )


def build_quotation_item(
    item_in,
    quotation_id: uuid.UUID,
) -> QuotationItem:
    """Create a QuotationItem model from request item data."""
    line_values = calculate_line(
        quantity=item_in.quantity,
        unit_price=item_in.unit_price,
        discount_rate=item_in.discount_rate,
        tax_rate=item_in.tax_rate,
    )

    return QuotationItem(
        quotation_id=quotation_id,
        product_id=item_in.product_id,
        description=item_in.description,
        quantity=item_in.quantity,
        unit=item_in.unit,
        unit_price=item_in.unit_price,
        discount_rate=item_in.discount_rate,
        tax_rate=item_in.tax_rate,
        subtotal=line_values["subtotal"],
        discount_amount=line_values["discount_amount"],
        tax_amount=line_values["tax_amount"],
        line_total=line_values["line_total"],
        sort_order=item_in.sort_order,
    )


def apply_totals(
    quotation: Quotation,
    items: list[QuotationItem],
) -> None:
    """Calculate and assign totals to a quotation."""
    totals = calculate_totals(items)

    quotation.subtotal = totals["subtotal"]
    quotation.discount_amount = totals["discount_amount"]
    quotation.tax_amount = totals["tax_amount"]
    quotation.total_amount = totals["total_amount"]


def create_quotation(
    db: Session,
    quotation_in: QuotationCreate,
    current_user: User,
) -> Quotation:
    """Create a quotation and its items."""
    customer = get_customer_for_organization(
        db=db,
        customer_id=quotation_in.customer_id,
        organization_id=current_user.organization_id,
    )

    if customer is None:
        raise ValueError(
            "Customer not found or does not belong to this organization"
        )

    quotation = Quotation(
        organization_id=current_user.organization_id,
        customer_id=quotation_in.customer_id,
        created_by=current_user.id,
        quotation_number=generate_quotation_number(
            db=db,
            organization_id=current_user.organization_id,
        ),
        status=QuotationStatus.DRAFT,
        issue_date=quotation_in.issue_date,
        expiry_date=quotation_in.expiry_date,
        currency=quotation_in.currency,
        notes=quotation_in.notes,
        terms=quotation_in.terms,
    )

    db.add(quotation)
    db.flush()

    quotation_items: list[QuotationItem] = []

    for item_in in quotation_in.items:
        validate_product_for_organization(
            db=db,
            product_id=item_in.product_id,
            organization_id=current_user.organization_id,
        )

        item = build_quotation_item(
            item_in=item_in,
            quotation_id=quotation.id,
        )

        quotation_items.append(item)

    db.add_all(quotation_items)

    apply_totals(
        quotation=quotation,
        items=quotation_items,
    )

    db.commit()

    created_quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation.id,
        organization_id=current_user.organization_id,
    )

    if created_quotation is None:
        raise RuntimeError(
            "Quotation was created but could not be retrieved"
        )

    return created_quotation


def get_quotation_by_id(
    db: Session,
    quotation_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Quotation | None:
    """Return one quotation belonging to an organization."""
    return db.scalar(
        select(Quotation)
        .options(
            selectinload(Quotation.items),
        )
        .where(
            Quotation.id == quotation_id,
            Quotation.organization_id == organization_id,
        )
        .execution_options(
            populate_existing=True,
        )
    )


def list_quotations(
    db: Session,
    organization_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: QuotationStatus | None = None,
) -> tuple[list[Quotation], int]:
    """Return a paginated list of quotations."""
    filters = [
        Quotation.organization_id == organization_id,
    ]

    if search:
        search_value = f"%{search.strip()}%"

        filters.append(
            or_(
                Quotation.quotation_number.ilike(search_value),
                Quotation.notes.ilike(search_value),
                Quotation.terms.ilike(search_value),
            )
        )

    if status is not None:
        filters.append(
            Quotation.status == status,
        )

    total = db.scalar(
        select(func.count())
        .select_from(Quotation)
        .where(*filters)
    ) or 0

    quotations = list(
        db.scalars(
            select(Quotation)
            .options(
                selectinload(Quotation.items),
            )
            .where(*filters)
            .order_by(
                Quotation.created_at.desc(),
            )
            .offset(
                (page - 1) * page_size,
            )
            .limit(page_size)
        ).all()
    )

    return quotations, total


def update_quotation(
    db: Session,
    quotation: Quotation,
    quotation_in: QuotationUpdate,
    current_user: User,
) -> Quotation:
    """Update a quotation and optionally replace all its items."""
    update_data = quotation_in.model_dump(
        exclude_unset=True,
        exclude={"items"},
    )

    new_status = update_data.get("status")

    if new_status is not None:
        validate_quotation_status_transition(
            current_status=quotation.status,
            new_status=new_status,
        )

    customer_id = update_data.get("customer_id")

    if customer_id is not None:
        customer = get_customer_for_organization(
            db=db,
            customer_id=customer_id,
            organization_id=current_user.organization_id,
        )

        if customer is None:
            raise ValueError(
                "Customer not found or does not belong to this organization"
            )

    issue_date = update_data.get(
        "issue_date",
        quotation.issue_date,
    )

    expiry_date = update_data.get(
        "expiry_date",
        quotation.expiry_date,
    )

    if expiry_date < issue_date:
        raise ValueError(
            "Expiry date cannot be earlier than issue date"
        )

    for field_name, value in update_data.items():
        setattr(
            quotation,
            field_name,
            value,
        )

    if quotation_in.items is not None:
        # Validate all replacement items before deleting existing items.
        for item_in in quotation_in.items:
            validate_product_for_organization(
                db=db,
                product_id=item_in.product_id,
                organization_id=current_user.organization_id,
            )

        # Because the relationship uses delete-orphan cascade,
        # clearing the collection deletes the previous items.
        quotation.items.clear()
        db.flush()

        replacement_items: list[QuotationItem] = []

        for item_in in quotation_in.items:
            item = build_quotation_item(
                item_in=item_in,
                quotation_id=quotation.id,
            )

            replacement_items.append(item)

        db.add_all(replacement_items)

        # Add the replacement items to the relationship exactly once.
        quotation.items.extend(replacement_items)

        apply_totals(
            quotation=quotation,
            items=replacement_items,
        )

    db.commit()

    updated_quotation = get_quotation_by_id(
        db=db,
        quotation_id=quotation.id,
        organization_id=current_user.organization_id,
    )

    if updated_quotation is None:
        raise RuntimeError(
            "Quotation was updated but could not be retrieved"
        )

    return updated_quotation


def delete_quotation(
    db: Session,
    quotation: Quotation,
) -> None:
    """Delete a quotation and its child items."""
    db.delete(quotation)
    db.commit()