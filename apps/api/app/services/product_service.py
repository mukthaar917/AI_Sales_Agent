import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def create_product(
    db: Session,
    organization_id: uuid.UUID,
    product_data: ProductCreate,
) -> Product:
    product = Product(
        organization_id=organization_id,
        **product_data.model_dump(),
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def get_product_by_id(
    db: Session,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
    include_inactive: bool = False,
) -> Product | None:
    query = select(Product).where(
        Product.id == product_id,
        Product.organization_id == organization_id,
    )

    if not include_inactive:
        query = query.where(Product.is_active.is_(True))

    return db.scalar(query)


def list_products(
    db: Session,
    organization_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Product], int]:
    filters = [
        Product.organization_id == organization_id,
    ]

    if not include_inactive:
        filters.append(Product.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"

        filters.append(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.description.ilike(term),
            )
        )

    total = db.scalar(
        select(func.count())
        .select_from(Product)
        .where(*filters)
    ) or 0

    offset = (page - 1) * page_size

    products = list(
        db.scalars(
            select(Product)
            .where(*filters)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )

    return products, total


def update_product(
    db: Session,
    product: Product,
    product_data: ProductUpdate,
) -> Product:
    updates = product_data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(product, field, value)

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def soft_delete_product(
    db: Session,
    product: Product,
) -> Product:
    product.is_active = False

    db.add(product)
    db.commit()
    db.refresh(product)

    return product