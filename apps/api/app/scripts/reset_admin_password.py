from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


ADMIN_EMAIL = "admin@example.com"
NEW_PASSWORD = "ChangeMe123!"


def reset_admin_password() -> None:
    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == ADMIN_EMAIL)
        )

        if user is None:
            print(f"User not found: {ADMIN_EMAIL}")
            return

        user.hashed_password = hash_password(NEW_PASSWORD)
        user.is_active = True

        db.commit()

        print(f"Password reset successfully for {ADMIN_EMAIL}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    reset_admin_password()