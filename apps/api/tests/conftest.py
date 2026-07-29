import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# This must exist before importing the application.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured. "
        "Set it to the dedicated ai_sales_agent_test database."
    )

# Ensure application settings also point to the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.organization import Organization
from app.models.user import User, UserRole


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Generator[None, None, None]:
    """
    Create all test tables before the test suite.

    Remove all test tables when the full suite finishes.
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """
    Run every test inside its own database transaction.

    Application code can call commit(), but the outer transaction is
    rolled back after the test. This prevents records from one test
    affecting another test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    db = TestingSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield db
    finally:
        db.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture()
def organization(
    db_session: Session,
) -> Organization:
    """Create an isolated organization for one test."""
    unique_value = uuid.uuid4().hex

    organization = Organization(
        name=f"Test Organization {unique_value}",
        slug=f"test-organization-{unique_value}",
    )

    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)

    return organization


@pytest.fixture()
def test_user(
    db_session: Session,
    organization: Organization,
) -> User:
    """Create an active test administrator."""
    user = User(
        organization_id=organization.id,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        full_name="Test Administrator",
        hashed_password=hash_password("TestPassword123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture()
def auth_headers(test_user: User) -> dict[str, str]:
    """Return an Authorization header for the test user."""
    token = create_access_token(subject=str(test_user.id))

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture()
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    """Provide a TestClient using the test database session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()