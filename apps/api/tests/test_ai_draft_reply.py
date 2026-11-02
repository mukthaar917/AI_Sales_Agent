from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.gmail_connection import GmailConnection
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.email import ReplySuggestion
from app.services.gmail.drafts import GmailDraftError
from app.services.reply_suggestions import ReplySuggestionError


EMAIL_BASE_URL = "/api/v1/email"


def _create_connection(
    db_session: Session,
    test_user: User,
    *,
    active: bool = True,
) -> GmailConnection:
    connection = GmailConnection(
        organization_id=test_user.organization_id,
        user_id=test_user.id,
        gmail_address="sales@example.com",
        access_token_encrypted="encrypted-access-token",
        refresh_token_encrypted="encrypted-refresh-token",
        scopes=(
            '["https://www.googleapis.com/auth/gmail.readonly",'
            '"https://www.googleapis.com/auth/gmail.compose"]'
        ),
        history_id="12345",
        is_active=active,
    )

    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)

    return connection


def _create_thread_and_message(
    db_session: Session,
    *,
    organization_id,
    connection: GmailConnection,
) -> tuple[EmailThread, EmailMessage]:
    now = datetime.now(timezone.utc)

    provider_thread_id = f"thread-{uuid.uuid4().hex}"

    thread = EmailThread(
        organization_id=organization_id,
        gmail_connection_id=connection.id,
        provider_thread_id=provider_thread_id,
        subject="Subject: Request for quotation for 10 laptops",
        participant_emails=[
            "customer@example.com",
            "sales@example.com",
        ],
        last_message_at=now,
        snippet=(
            "Please send pricing, availability, "
            "delivery time and payment terms."
        ),
        unread=False,
    )

    db_session.add(thread)
    db_session.flush()

    message = EmailMessage(
        organization_id=organization_id,
        gmail_connection_id=connection.id,
        thread_id=thread.id,
        provider_message_id=f"message-{uuid.uuid4().hex}",
        provider_thread_id=provider_thread_id,
        internet_message_id="<customer-message@example.com>",
        in_reply_to=None,
        references_header=None,
        sender_name="Customer",
        sender_email="customer@example.com",
        recipient_emails=["sales@example.com"],
        cc_emails=[],
        subject="Request for quotation for 10 laptops",
        text_body=(
            "We would like to purchase 10 laptops. "
            "Please provide pricing, availability, "
            "delivery time and payment terms."
        ),
        html_body=None,
        received_at=now,
        sent_at=None,
        direction="incoming",
        unread=False,
        has_attachments=False,
        raw_headers={},
    )

    db_session.add(message)
    db_session.commit()

    db_session.refresh(thread)
    db_session.refresh(message)

    return thread, message


def test_ai_draft_reply_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        f"{EMAIL_BASE_URL}/threads/"
        f"{uuid.uuid4()}/ai-draft-reply",
    )

    assert response.status_code == 401


def test_ai_draft_reply_creates_grounded_gmail_draft(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _create_connection(
        db_session,
        test_user,
    )

    thread, _ = _create_thread_and_message(
        db_session,
        organization_id=test_user.organization_id,
        connection=connection,
    )

    generated_subject = (
        "Re: Request for quotation for 10 laptops"
    )

    generated_body = (
        "Payment terms are Net 30. "
        "Standard delivery for in-stock business laptops "
        "is 5-7 business days after order confirmation. "
        "Pricing and current availability require confirmation."
    )

    captured: dict = {}

    class FakeReplySuggestionService:
        def generate(
            self,
            *,
            db,
            organization_id,
            thread,
            messages,
        ):
            assert db is db_session
            assert organization_id == test_user.organization_id
            assert len(messages) == 1

            return [
                ReplySuggestion(
                    subject=generated_subject,
                    body=generated_body,
                )
            ]

    class FakeGmailClient:
        def __init__(
            self,
            *,
            access_token,
            scopes,
        ):
            captured["access_token"] = access_token
            captured["scopes"] = scopes

    class FakeGmailDraftService:
        def __init__(
            self,
            gmail_client,
        ):
            captured["gmail_client"] = gmail_client

        def create_thread_reply_draft(
            self,
            *,
            thread,
            latest_message,
            subject,
            body,
            attachments=None,
        ):
            captured["thread_id"] = thread.id
            captured["latest_message_id"] = latest_message.id
            captured["subject"] = subject
            captured["body"] = body
            captured["attachments"] = attachments

            return SimpleNamespace(
                draft_id="draft-test-123",
                message_id="message-test-456",
            )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.ReplySuggestionService",
        FakeReplySuggestionService,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email._get_valid_gmail_access_token",
        lambda **kwargs: "test-access-token",
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.GmailClient",
        FakeGmailClient,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.GmailDraftService",
        FakeGmailDraftService,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 200

    assert response.json() == {
        "thread_id": str(thread.id),
        "draft_id": "draft-test-123",
        "message_id": "message-test-456",
        "status": "draft",
    }

    assert captured["access_token"] == "test-access-token"

    assert captured["thread_id"] == thread.id

    assert captured["subject"] == generated_subject

    assert captured["body"] == generated_body

    assert captured["attachments"] is None


def test_ai_draft_reply_rejects_other_tenant_thread(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    other_organization = Organization(
        name="Other Organization",
        slug=f"other-org-{uuid.uuid4().hex}",
    )

    db_session.add(other_organization)
    db_session.flush()

    other_user = User(
        organization_id=other_organization.id,
        email=f"other-{uuid.uuid4().hex}@example.com",
        full_name="Other User",
        hashed_password=hash_password(
            "OtherPassword123!"
        ),
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(other_user)
    db_session.flush()

    other_connection = GmailConnection(
        organization_id=other_organization.id,
        user_id=other_user.id,
        gmail_address="other@example.com",
        access_token_encrypted="encrypted-access-token",
        refresh_token_encrypted="encrypted-refresh-token",
        scopes='["scope"]',
        is_active=True,
    )

    db_session.add(other_connection)
    db_session.flush()

    other_thread, _ = _create_thread_and_message(
        db_session,
        organization_id=other_organization.id,
        connection=other_connection,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{other_thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Email thread was not found.",
    }


def test_ai_draft_reply_requires_active_gmail_connection(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _create_connection(
        db_session,
        test_user,
        active=False,
    )

    thread, _ = _create_thread_and_message(
        db_session,
        organization_id=test_user.organization_id,
        connection=connection,
    )

    class FakeReplySuggestionService:
        def generate(self, **kwargs):
            return [
                ReplySuggestion(
                    subject="Re: Test",
                    body="Grounded test reply.",
                )
            ]

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.ReplySuggestionService",
        FakeReplySuggestionService,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "No active Gmail connection was found.",
    }


def test_ai_failure_does_not_create_gmail_draft(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _create_connection(
        db_session,
        test_user,
    )

    thread, _ = _create_thread_and_message(
        db_session,
        organization_id=test_user.organization_id,
        connection=connection,
    )

    draft_called = False

    class FailingReplySuggestionService:
        def generate(self, **kwargs):
            raise ReplySuggestionError(
                "Unable to generate a grounded reply suggestion."
            )

    class UnexpectedDraftService:
        def __init__(self, *args, **kwargs):
            nonlocal draft_called
            draft_called = True

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.ReplySuggestionService",
        FailingReplySuggestionService,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.GmailDraftService",
        UnexpectedDraftService,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 422

    assert draft_called is False


def test_ai_draft_reply_rejects_empty_suggestions(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _create_connection(
        db_session,
        test_user,
    )

    thread, _ = _create_thread_and_message(
        db_session,
        organization_id=test_user.organization_id,
        connection=connection,
    )

    class EmptyReplySuggestionService:
        def generate(self, **kwargs):
            return []

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.ReplySuggestionService",
        EmptyReplySuggestionService,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": "No AI reply suggestion was generated.",
    }


def test_gmail_draft_failure_returns_bad_gateway(
    client: TestClient,
    db_session: Session,
    test_user: User,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _create_connection(
        db_session,
        test_user,
    )

    thread, _ = _create_thread_and_message(
        db_session,
        organization_id=test_user.organization_id,
        connection=connection,
    )

    class FakeReplySuggestionService:
        def generate(self, **kwargs):
            return [
                ReplySuggestion(
                    subject="Re: Request for quotation",
                    body="Grounded AI reply.",
                )
            ]

    class FakeGmailClient:
        def __init__(self, **kwargs):
            pass

    class FailingGmailDraftService:
        def __init__(self, gmail_client):
            pass

        def create_thread_reply_draft(
            self,
            **kwargs,
        ):
            raise GmailDraftError(
                "Unable to create Gmail draft."
            )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.ReplySuggestionService",
        FakeReplySuggestionService,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email._get_valid_gmail_access_token",
        lambda **kwargs: "test-access-token",
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.GmailClient",
        FakeGmailClient,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.email.GmailDraftService",
        FailingGmailDraftService,
    )

    response = client.post(
        (
            f"{EMAIL_BASE_URL}/threads/"
            f"{thread.id}/ai-draft-reply"
        ),
        headers=auth_headers,
    )

    assert response.status_code == 502

    assert response.json() == {
        "detail": "Unable to create Gmail draft.",
    }