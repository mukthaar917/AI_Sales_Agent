from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user matching the supplied email address."""
    normalized_email = email.strip().lower()

    statement = select(User).where(
        func.lower(User.email) == normalized_email
    )

    return db.scalar(statement)


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Validate user credentials and return the matching active user."""
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user