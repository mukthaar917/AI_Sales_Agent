import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def create_customer(
    db: Session,
    organization_id: uuid.UUID,
    customer_data: CustomerCreate,
) -> Customer:
    payload = customer_data.model_dump()

    website = payload.get("website")
    if website is not None:
        payload["website"] = str(website)

    customer = Customer(
        organization_id=organization_id,
        **payload,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


def find_active_customer_by_email(
    db: Session,
    organization_id: uuid.UUID,
    email: str,
) -> Customer | None:
    """Return an active customer matching an email in the organization."""

    normalized_email = email.strip().lower()

    if not normalized_email:
        return None

    return db.scalar(
        select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
            func.lower(Customer.email) == normalized_email,
        )
    )


def get_customer_by_id(
    db: Session,
    organization_id: uuid.UUID,
    customer_id: uuid.UUID,
    include_inactive: bool = False,
) -> Customer | None:
    query = select(Customer).where(
        Customer.id == customer_id,
        Customer.organization_id == organization_id,
    )

    if not include_inactive:
        query = query.where(Customer.is_active.is_(True))

    return db.scalar(query)


def list_customers(
    db: Session,
    organization_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Customer], int]:
    filters = [
        Customer.organization_id == organization_id,
    ]

    if not include_inactive:
        filters.append(Customer.is_active.is_(True))

    if search:
        search_term = f"%{search.strip()}%"

        filters.append(
            or_(
                Customer.company_name.ilike(search_term),
                Customer.contact_name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term),
            )
        )

    count_query = (
        select(func.count())
        .select_from(Customer)
        .where(*filters)
    )

    total = db.scalar(count_query) or 0

    offset = (page - 1) * page_size

    customers_query = (
        select(Customer)
        .where(*filters)
        .order_by(Customer.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    customers = list(
        db.scalars(customers_query).all()
    )

    return customers, total


def update_customer(
    db: Session,
    customer: Customer,
    customer_data: CustomerUpdate,
) -> Customer:
    updates = customer_data.model_dump(
        exclude_unset=True,
    )

    if (
        "website" in updates
        and updates["website"] is not None
    ):
        updates["website"] = str(
            updates["website"]
        )

    for field, value in updates.items():
        setattr(customer, field, value)

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


def soft_delete_customer(
    db: Session,
    customer: Customer,
) -> Customer:
    customer.is_active = False

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer