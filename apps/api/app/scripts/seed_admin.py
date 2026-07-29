from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "ChangeMe123!"

ORG_NAME = "Default Organization"
ORG_SLUG = "default"


def main() -> None:
    db = SessionLocal()

    try:
        organization = db.scalar(
            select(Organization).where(
                Organization.slug == ORG_SLUG
            )
        )

        if organization is None:
            organization = Organization(
                name=ORG_NAME,
                slug=ORG_SLUG,
            )
            db.add(organization)
            db.flush()

        existing_user = db.scalar(
            select(User).where(
                User.email == ADMIN_EMAIL
            )
        )

        if existing_user:
            print("Admin user already exists.")
            return

        admin = User(
            organization_id=organization.id,
            email=ADMIN_EMAIL,
            full_name="System Administrator",
            hashed_password=hash_password(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("Admin user created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()