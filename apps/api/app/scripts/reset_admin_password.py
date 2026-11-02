from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


OLD_EMAIL = "admin@example.com"
NEW_EMAIL = "truefoxaiinc234@gmail.com"
NEW_PASSWORD = "YourNewStrongPassword123!"


def reset_admin_credentials() -> None:
    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == OLD_EMAIL)
        )

        if user is None:
            print(f"User not found: {OLD_EMAIL}")
            return

        # Change email
        user.email = NEW_EMAIL

        # Change password using the project's password hashing
        user.hashed_password = hash_password(NEW_PASSWORD)

        # Make sure admin account is active
        user.is_active = True

        db.commit()

        print("Admin credentials updated successfully")
        print(f"Old email: {OLD_EMAIL}")
        print(f"New email: {NEW_EMAIL}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    reset_admin_credentials()