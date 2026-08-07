"""Email synchronization and inbox API endpoints."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.encryption import (
    EncryptionConfigurationError,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
)
from app.db.session import get_db
from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.gmail_connection import GmailConnection
from app.models.user import User
from app.schemas.email import (
    EmailMessageResponse,
    EmailThreadDetail,
    EmailThreadListResponse,
    EmailThreadSummary,
    EmailThreadSummaryResponse,
)
from app.services.email_summary import (
    EmailSummaryError,
    EmailSummaryService,
)
from app.services.gmail.client import (
    GmailClient,
    GmailClientError,
)
from app.services.gmail.oauth import (
    GmailOAuthError,
    GmailOAuthService,
)
from app.services.gmail.sync import (
    GmailSyncError,
    GmailSyncService,
)


router = APIRouter()


class GmailSyncResponse(BaseModel):
    """Gmail synchronization statistics."""

    fetched: int
    created: int
    updated: int
    skipped: int
    failed: int


def _deserialize_scopes(
    scopes_value: str | None,
) -> list[str]:
    """Deserialize stored OAuth scopes safely."""

    if not scopes_value:
        return []

    try:
        parsed_scopes = json.loads(scopes_value)

        if isinstance(parsed_scopes, list):
            return [
                str(scope).strip()
                for scope in parsed_scopes
                if str(scope).strip()
            ]
    except (json.JSONDecodeError, TypeError):
        pass

    return [
        scope.strip()
        for scope in scopes_value.replace(",", " ").split()
        if scope.strip()
    ]


def _get_active_gmail_connection(
    db: Session,
    current_user: User,
) -> GmailConnection | None:
    """Return the active Gmail connection for one user and tenant."""

    statement = select(GmailConnection).where(
        GmailConnection.organization_id
        == current_user.organization_id,
        GmailConnection.user_id
        == current_user.id,
        GmailConnection.is_active.is_(True),
    )

    return db.scalar(statement)


def _thread_message_order():
    """Return the consistent chronological ordering for thread messages."""

    return (
        case(
            (
                EmailMessage.received_at.is_not(None),
                EmailMessage.received_at,
            ),
            else_=EmailMessage.sent_at,
        ).asc().nullslast(),
        EmailMessage.created_at.asc(),
    )


@router.post(
    "/sync",
    response_model=GmailSyncResponse,
    status_code=status.HTTP_200_OK,
)
def sync_gmail_inbox(
    max_results: int = Query(
        default=25,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailSyncResponse:
    """Synchronize Gmail inbox messages for the authenticated user."""

    connection = _get_active_gmail_connection(
        db=db,
        current_user=current_user,
    )

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Gmail connection was found.",
        )

    try:
        access_token = decrypt_secret(
            connection.access_token_encrypted
        )

        token_expired = (
            connection.token_expiry is not None
            and connection.token_expiry
            <= datetime.now(timezone.utc)
        )

        if token_expired:
            if not connection.refresh_token_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Gmail must be reconnected before "
                        "synchronization."
                    ),
                )

            refresh_token = decrypt_secret(
                connection.refresh_token_encrypted
            )

            refreshed_credentials = (
                GmailOAuthService()
                .refresh_access_token(refresh_token)
            )

            refreshed_access_token = str(
                refreshed_credentials.get(
                    "access_token",
                    "",
                )
            ).strip()

            if not refreshed_access_token:
                raise GmailOAuthError(
                    "Google did not return an access token."
                )

            access_token = refreshed_access_token

            connection.access_token_encrypted = encrypt_secret(
                access_token
            )

            connection.token_expiry = (
                refreshed_credentials.get("token_expiry")
            )

            refreshed_refresh_token = str(
                refreshed_credentials.get(
                    "refresh_token",
                    "",
                )
                or ""
            ).strip()

            if refreshed_refresh_token:
                connection.refresh_token_encrypted = (
                    encrypt_secret(refreshed_refresh_token)
                )

            db.add(connection)
            db.commit()
            db.refresh(connection)

        gmail_client = GmailClient(
            access_token=access_token,
            scopes=_deserialize_scopes(
                connection.scopes
            ),
        )

        sync_service = GmailSyncService(
            db=db,
            gmail_client=gmail_client,
            connection=connection,
        )

        statistics = sync_service.sync_inbox(
            max_results=max_results
        )

        return GmailSyncResponse(**statistics)

    except HTTPException:
        raise

    except (
        EncryptionConfigurationError,
        SecretDecryptionError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored Gmail credentials are unavailable.",
        ) from None

    except GmailOAuthError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to refresh the Gmail connection.",
        ) from None

    except (
        GmailClientError,
        GmailSyncError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to synchronize the Gmail inbox.",
        ) from None

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save Gmail synchronization results.",
        ) from None


@router.get(
    "/threads",
    response_model=EmailThreadListResponse,
    status_code=status.HTTP_200_OK,
)
def list_email_threads(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    sender: str | None = Query(
        default=None,
        min_length=1,
        max_length=320,
    ),
    unread: bool | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadListResponse:
    """Return synchronized email threads for the current organization."""

    thread_filters = [
        EmailThread.organization_id
        == current_user.organization_id,
    ]

    if unread is not None:
        thread_filters.append(
            EmailThread.unread.is_(unread)
        )

    normalized_search = (
        search.strip()
        if search
        else None
    )

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        sender_thread_ids = (
            select(EmailMessage.thread_id)
            .where(
                EmailMessage.organization_id
                == current_user.organization_id,
                EmailMessage.sender_email.ilike(
                    search_pattern
                ),
            )
        )

        thread_filters.append(
            or_(
                EmailThread.subject.ilike(
                    search_pattern
                ),
                EmailThread.snippet.ilike(
                    search_pattern
                ),
                EmailThread.id.in_(sender_thread_ids),
            )
        )

    normalized_sender = (
        sender.strip()
        if sender
        else None
    )

    if normalized_sender:
        sender_pattern = f"%{normalized_sender}%"

        sender_thread_ids = (
            select(EmailMessage.thread_id)
            .where(
                EmailMessage.organization_id
                == current_user.organization_id,
                EmailMessage.sender_email.ilike(
                    sender_pattern
                ),
            )
        )

        thread_filters.append(
            EmailThread.id.in_(sender_thread_ids)
        )

    total_statement = (
        select(func.count())
        .select_from(EmailThread)
        .where(*thread_filters)
    )

    total = db.scalar(total_statement) or 0

    message_count_subquery = (
        select(
            EmailMessage.thread_id.label(
                "thread_id"
            ),
            func.count(
                EmailMessage.id
            ).label(
                "message_count"
            ),
        )
        .where(
            EmailMessage.organization_id
            == current_user.organization_id
        )
        .group_by(
            EmailMessage.thread_id
        )
        .subquery()
    )

    thread_statement = (
        select(
            EmailThread,
            func.coalesce(
                message_count_subquery.c.message_count,
                0,
            ).label("message_count"),
        )
        .outerjoin(
            message_count_subquery,
            message_count_subquery.c.thread_id
            == EmailThread.id,
        )
        .where(*thread_filters)
        .order_by(
            EmailThread.last_message_at.desc().nullslast(),
            EmailThread.created_at.desc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    rows = db.execute(
        thread_statement
    ).all()

    items = [
        EmailThreadSummary(
            id=thread.id,
            provider_thread_id=(
                thread.provider_thread_id
            ),
            subject=thread.subject,
            snippet=thread.snippet,
            participant_emails=(
                thread.participant_emails or []
            ),
            last_message_at=thread.last_message_at,
            unread=thread.unread,
            message_count=int(message_count),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )
        for thread, message_count in rows
    ]

    total_pages = (
        math.ceil(total / page_size)
        if total
        else 0
    )

    return EmailThreadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/threads/{thread_id}",
    response_model=EmailThreadDetail,
    status_code=status.HTTP_200_OK,
)
def get_email_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadDetail:
    """Return one email thread and its messages."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    return EmailThreadDetail(
        id=thread.id,
        provider_thread_id=(
            thread.provider_thread_id
        ),
        subject=thread.subject,
        snippet=thread.snippet,
        participant_emails=(
            thread.participant_emails or []
        ),
        last_message_at=thread.last_message_at,
        unread=thread.unread,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        messages=[
            EmailMessageResponse.model_validate(
                message
            )
            for message in messages
        ],
    )


@router.post(
    "/threads/{thread_id}/summary",
    response_model=EmailThreadSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def summarize_email_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadSummaryResponse:
    """Generate a concise summary for one synchronized email thread."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    try:
        summary = EmailSummaryService().summarize(
            thread=thread,
            messages=list(messages),
        )
    except EmailSummaryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return EmailThreadSummaryResponse(
        thread_id=thread.id,
        summary=summary,
        message_count=len(messages),
    )


@router.get(
    "/messages/{message_id}",
    response_model=EmailMessageResponse,
    status_code=status.HTTP_200_OK,
)
def get_email_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailMessageResponse:
    """Return one synchronized email message."""

    message = db.scalar(
        select(EmailMessage).where(
            EmailMessage.id == message_id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email message was not found.",
        )

    return EmailMessageResponse.model_validate(
        message
    )