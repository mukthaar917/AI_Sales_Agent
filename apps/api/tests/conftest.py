import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# -------------------------------------------------------
# Resolve test database
# -------------------------------------------------------

TEST_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or settings.test_database_url
)

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured.\n"
        "Add TEST_DATABASE_URL to your .env file."
    )

# Ensure the application uses the test database.
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
    bind=test_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db_session():
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
def organization(db_session):
    unique = uuid.uuid4().hex

    organization = Organization(
        name=f"Test Organization {unique}",
        slug=f"test-org-{unique}",
    )

    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)

    return organization


@pytest.fixture()
def test_user(db_session, organization):
    user = User(
        organization_id=organization.id,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        full_name="Test Admin",
        hashed_password=hash_password("TestPassword123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture()
def auth_headers(test_user):
    token = create_access_token(subject=str(test_user.id))

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()