"""Email synchronization API endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
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
from app.models.gmail_connection import GmailConnection
from app.models.user import User
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

    # Backward compatibility for whitespace- or comma-separated scopes.
    return [
        scope.strip()
        for scope in scopes_value.replace(",", " ").split()
        if scope.strip()
    ]


def _get_active_gmail_connection(
    db: Session,
    current_user: User,
) -> GmailConnection | None:
    """Return the active Gmail connection for the current user and tenant."""

    statement = select(GmailConnection).where(
        GmailConnection.organization_id
        == current_user.organization_id,
        GmailConnection.user_id
        == current_user.id,
        GmailConnection.is_active.is_(True),
    )

    return db.scalar(statement)


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