from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.gmail import _create_oauth_state
from app.models.gmail_connection import GmailConnection
from app.models.user import User


GMAIL_BASE_URL = "/api/v1/gmail"


def test_gmail_authorize_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get(
        f"{GMAIL_BASE_URL}/oauth/authorize",
    )

    assert response.status_code == 401


def test_gmail_connection_requires_authentication(
    client: TestClient,
) -> None:
    response = client.get(
        f"{GMAIL_BASE_URL}/connection",
    )

    assert response.status_code == 401


def test_gmail_disconnect_requires_authentication(
    client: TestClient,
) -> None:
    response = client.delete(
        f"{GMAIL_BASE_URL}/connection",
    )

    assert response.status_code == 401


def test_authorize_returns_signed_authorization_url(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    class FakeOAuthService:
        def build_authorization_url(self):
            return (
                "https://accounts.google.com/o/oauth2/v2/auth"
                "?client_id=test-client"
                "&state=provider-state",
                "provider-state",
            )

    monkeypatch.setattr(
        "app.api.v1.endpoints.gmail.GmailOAuthService",
        FakeOAuthService,
    )

    response = client.get(
        f"{GMAIL_BASE_URL}/oauth/authorize",
        headers=auth_headers,
    )

    assert response.status_code == 200

    authorization_url = response.json()["authorization_url"]
    parsed_url = urlparse(authorization_url)
    query = parse_qs(parsed_url.query)

    assert parsed_url.netloc == "accounts.google.com"
    assert query["client_id"] == ["test-client"]
    assert query["state"]
    assert query["state"][0] != "provider-state"


def test_connection_returns_disconnected_when_absent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{GMAIL_BASE_URL}/connection",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "email_address": None,
        "scopes": [],
        "token_expiry": None,
        "history_id": None,
    }


def test_callback_rejects_invalid_state(
    client: TestClient,
) -> None:
    response = client.get(
        f"{GMAIL_BASE_URL}/oauth/callback",
        params={
            "code": "test-code",
            "state": "invalid-state",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid OAuth state",
    }


def test_callback_creates_gmail_connection(
    client: TestClient,
    db_session: Session,
    test_user: User,
    monkeypatch,
) -> None:
    token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    class FakeOAuthService:
        def exchange_code_for_tokens(self, code: str):
            assert code == "test-code"

            return {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "token_expiry": token_expiry,
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.readonly",
                ],
            }

        def fetch_gmail_profile(self, access_token: str):
            assert access_token == "test-access-token"

            return {
                "email_address": "sales@example.com",
                "history_id": "123456",
            }

    monkeypatch.setattr(
        "app.api.v1.endpoints.gmail.GmailOAuthService",
        FakeOAuthService,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.gmail.encrypt_secret",
        lambda value: f"encrypted:{value}",
    )

    state = _create_oauth_state(
        user=test_user,
        provider_state="provider-state",
    )

    response = client.get(
        f"{GMAIL_BASE_URL}/oauth/callback",
        params={
            "code": "test-code",
            "state": state,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["connected"] is True
    assert data["email_address"] == "sales@example.com"
    assert data["scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    assert data["history_id"] == "123456"
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "access_token_encrypted" not in data
    assert "refresh_token_encrypted" not in data

    connection = db_session.scalar(
        select(GmailConnection).where(
            GmailConnection.organization_id
            == test_user.organization_id,
            GmailConnection.user_id == test_user.id,
        )
    )

    assert connection is not None
    assert connection.gmail_address == "sales@example.com"
    assert (
        connection.access_token_encrypted
        == "encrypted:test-access-token"
    )
    assert (
        connection.refresh_token_encrypted
        == "encrypted:test-refresh-token"
    )
    assert connection.history_id == "123456"
    assert connection.is_active is True


def test_callback_preserves_existing_refresh_token(
    client: TestClient,
    db_session: Session,
    test_user: User,
    monkeypatch,
) -> None:
    existing_connection = GmailConnection(
        organization_id=test_user.organization_id,
        user_id=test_user.id,
        gmail_address="old@example.com",
        access_token_encrypted="encrypted:old-access-token",
        refresh_token_encrypted="encrypted:existing-refresh-token",
        scopes=None,
        history_id="old-history",
        is_active=True,
    )

    db_session.add(existing_connection)
    db_session.commit()

    class FakeOAuthService:
        def exchange_code_for_tokens(self, code: str):
            return {
                "access_token": "new-access-token",
                "refresh_token": None,
                "token_expiry": None,
                "scopes": [],
            }

        def fetch_gmail_profile(self, access_token: str):
            return {
                "email_address": "updated@example.com",
                "history_id": "new-history",
            }

    monkeypatch.setattr(
        "app.api.v1.endpoints.gmail.GmailOAuthService",
        FakeOAuthService,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.gmail.encrypt_secret",
        lambda value: f"encrypted:{value}",
    )

    state = _create_oauth_state(
        user=test_user,
        provider_state="provider-state",
    )

    response = client.get(
        f"{GMAIL_BASE_URL}/oauth/callback",
        params={
            "code": "test-code",
            "state": state,
        },
    )

    assert response.status_code == 200

    db_session.refresh(existing_connection)

    assert (
        existing_connection.access_token_encrypted
        == "encrypted:new-access-token"
    )
    assert (
        existing_connection.refresh_token_encrypted
        == "encrypted:existing-refresh-token"
    )
    assert existing_connection.gmail_address == "updated@example.com"
    assert existing_connection.history_id == "new-history"


def test_connection_returns_safe_connected_response(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    connection = GmailConnection(
        organization_id=test_user.organization_id,
        user_id=test_user.id,
        gmail_address="connected@example.com",
        access_token_encrypted="secret-access-token",
        refresh_token_encrypted="secret-refresh-token",
        scopes='["scope-one", "scope-two"]',
        history_id="789",
        is_active=True,
    )

    db_session.add(connection)
    db_session.commit()

    response = client.get(
        f"{GMAIL_BASE_URL}/connection",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "connected": True,
        "email_address": "connected@example.com",
        "scopes": ["scope-one", "scope-two"],
        "token_expiry": None,
        "history_id": "789",
    }

    assert "access_token_encrypted" not in data
    assert "refresh_token_encrypted" not in data


def test_disconnect_deactivates_and_clears_connection(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    connection = GmailConnection(
        organization_id=test_user.organization_id,
        user_id=test_user.id,
        gmail_address="connected@example.com",
        access_token_encrypted="encrypted-access-token",
        refresh_token_encrypted="encrypted-refresh-token",
        scopes='["scope-one"]',
        history_id="999",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        last_synced_at=datetime.now(timezone.utc),
        is_active=True,
    )

    db_session.add(connection)
    db_session.commit()

    response = client.delete(
        f"{GMAIL_BASE_URL}/connection",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
    }

    db_session.refresh(connection)

    assert connection.is_active is False
    assert connection.access_token_encrypted == ""
    assert connection.refresh_token_encrypted is None
    assert connection.token_expiry is None
    assert connection.history_id is None
    assert connection.last_synced_at is None


def test_disconnect_is_idempotent_without_connection(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.delete(
        f"{GMAIL_BASE_URL}/connection",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
    }