"""Gmail OAuth and connection API endpoints."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.encryption import (
    EncryptionConfigurationError,
    encrypt_secret,
)
from app.db.session import get_db
from app.models.gmail_connection import GmailConnection
from app.models.user import User
from app.schemas.gmail import (
    GmailAuthorizationResponse,
    GmailConnectionResponse,
    GmailDisconnectResponse,
)
from app.services.gmail.oauth import (
    GmailOAuthError,
    GmailOAuthService,
)


router = APIRouter()


OAUTH_STATE_PURPOSE = "gmail_oauth"
OAUTH_STATE_EXPIRE_MINUTES = 10


def _create_oauth_state(user: User, provider_state: str) -> str:
    """Create a short-lived signed OAuth state tied to a user and tenant."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user.id),
        "organization_id": str(user.organization_id),
        "provider_state": provider_state,
        "purpose": OAUTH_STATE_PURPOSE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _decode_oauth_state(state_value: str) -> dict[str, Any]:
    """Validate and decode a signed Gmail OAuth state."""
    try:
        payload = jwt.decode(
            state_value,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        ) from exc

    if payload.get("purpose") != OAUTH_STATE_PURPOSE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    if not payload.get("sub") or not payload.get("organization_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    return payload


def _replace_url_state(
    authorization_url: str,
    signed_state: str,
) -> str:
    """Replace the state query parameter in Google's authorization URL."""
    parsed_url = urlsplit(authorization_url)

    query_parameters = dict(
        parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
    )
    query_parameters["state"] = signed_state

    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            urlencode(query_parameters),
            parsed_url.fragment,
        )
    )


def _serialize_scopes(scopes: list[str] | None) -> str | None:
    """Serialize OAuth scopes for storage in the Text database column."""
    if not scopes:
        return None

    return json.dumps(scopes)


def _deserialize_scopes(scopes_value: str | None) -> list[str]:
    """Deserialize stored OAuth scopes safely."""
    if not scopes_value:
        return []

    try:
        parsed_scopes = json.loads(scopes_value)
    except (json.JSONDecodeError, TypeError):
        # Support previously stored whitespace-separated scopes.
        return [
            scope.strip()
            for scope in scopes_value.replace(",", " ").split()
            if scope.strip()
        ]

    if not isinstance(parsed_scopes, list):
        return []

    return [
        str(scope).strip()
        for scope in parsed_scopes
        if str(scope).strip()
    ]


def _connection_response(
    connection: GmailConnection | None,
) -> GmailConnectionResponse:
    """Convert a connection model into a credential-safe response."""
    if connection is None or not connection.is_active:
        return GmailConnectionResponse(
            connected=False,
            email_address=None,
            scopes=[],
            token_expiry=None,
            history_id=None,
        )

    return GmailConnectionResponse(
        connected=True,
        email_address=connection.gmail_address,
        scopes=_deserialize_scopes(connection.scopes),
        token_expiry=connection.token_expiry,
        history_id=connection.history_id,
    )


def _get_user_connection(
    db: Session,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    include_inactive: bool = False,
) -> GmailConnection | None:
    """Return a Gmail connection scoped to one organization and user."""
    statement = select(GmailConnection).where(
        GmailConnection.organization_id == organization_id,
        GmailConnection.user_id == user_id,
    )

    if not include_inactive:
        statement = statement.where(
            GmailConnection.is_active.is_(True),
        )

    return db.scalar(statement)


@router.get(
    "/oauth/authorize",
    response_model=GmailAuthorizationResponse,
    status_code=status.HTTP_200_OK,
)
def authorize_gmail(
    current_user: User = Depends(get_current_user),
) -> GmailAuthorizationResponse:
    """Create a Google OAuth authorization URL for the current user."""
    oauth_service = GmailOAuthService()

    try:
        authorization_url, provider_state = (
            oauth_service.build_authorization_url()
        )
    except GmailOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to start Gmail authorization",
        ) from exc

    signed_state = _create_oauth_state(
        user=current_user,
        provider_state=provider_state,
    )

    safe_authorization_url = _replace_url_state(
        authorization_url=authorization_url,
        signed_state=signed_state,
    )

    return GmailAuthorizationResponse(
        authorization_url=safe_authorization_url,
    )


@router.get(
    "/oauth/callback",
    response_model=GmailConnectionResponse,
    status_code=status.HTTP_200_OK,
)
def gmail_oauth_callback(
    code: str = Query(
        ...,
        min_length=1,
        description="Authorization code returned by Google",
    ),
    state_value: str = Query(
        ...,
        alias="state",
        min_length=1,
        description="Signed OAuth state",
    ),
    db: Session = Depends(get_db),
) -> GmailConnectionResponse:
    """Handle Google's OAuth callback and save encrypted credentials."""
    normalized_code = code.strip()
    normalized_state = state_value.strip()

    if not normalized_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required",
        )

    if not normalized_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state is required",
        )

    state_payload = _decode_oauth_state(normalized_state)

    try:
        user_id = uuid.UUID(state_payload["sub"])
        organization_id = uuid.UUID(
            state_payload["organization_id"]
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        ) from exc

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    oauth_service = GmailOAuthService()

    try:
        token_data = oauth_service.exchange_code_for_tokens(
            normalized_code
        )

        access_token = token_data.get("access_token")

        if not access_token:
            raise GmailOAuthError(
                "Google did not return an access token."
            )

        gmail_profile = oauth_service.fetch_gmail_profile(
            access_token
        )

        encrypted_access_token = encrypt_secret(access_token)

        existing_connection = _get_user_connection(
            db,
            organization_id=organization_id,
            user_id=user_id,
            include_inactive=True,
        )

        refresh_token = token_data.get("refresh_token")

        if refresh_token:
            encrypted_refresh_token = encrypt_secret(
                refresh_token
            )
        elif existing_connection is not None:
            # Google may omit the refresh token during repeat consent.
            encrypted_refresh_token = (
                existing_connection.refresh_token_encrypted
            )
        else:
            encrypted_refresh_token = None

        serialized_scopes = _serialize_scopes(
            token_data.get("scopes")
        )

        if existing_connection is None:
            connection = GmailConnection(
                organization_id=organization_id,
                user_id=user_id,
                gmail_address=gmail_profile["email_address"],
                access_token_encrypted=encrypted_access_token,
                refresh_token_encrypted=encrypted_refresh_token,
                token_expiry=token_data.get("token_expiry"),
                scopes=serialized_scopes,
                history_id=gmail_profile.get("history_id"),
                is_active=True,
            )
            db.add(connection)
        else:
            connection = existing_connection
            connection.gmail_address = gmail_profile[
                "email_address"
            ]
            connection.access_token_encrypted = (
                encrypted_access_token
            )
            connection.refresh_token_encrypted = (
                encrypted_refresh_token
            )
            connection.token_expiry = token_data.get(
                "token_expiry"
            )
            connection.scopes = serialized_scopes
            connection.history_id = gmail_profile.get(
                "history_id"
            )
            connection.is_active = True

        db.commit()
        db.refresh(connection)

    except GmailOAuthError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to complete Gmail authorization",
        ) from exc
    except EncryptionConfigurationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential encryption is not configured",
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Gmail authorization response",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save Gmail connection",
        ) from exc

    return _connection_response(connection)


@router.get(
    "/connection",
    response_model=GmailConnectionResponse,
    status_code=status.HTTP_200_OK,
)
def get_gmail_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailConnectionResponse:
    """Return the current user's Gmail connection status."""
    connection = _get_user_connection(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )

    return _connection_response(connection)


@router.delete(
    "/connection",
    response_model=GmailDisconnectResponse,
    status_code=status.HTTP_200_OK,
)
def disconnect_gmail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailDisconnectResponse:
    """Deactivate Gmail and clear stored OAuth credentials."""
    connection = _get_user_connection(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        include_inactive=True,
    )

    if connection is None:
        return GmailDisconnectResponse(connected=False)

    try:
        connection.is_active = False

        # Clear stored credentials when disconnecting.
        connection.access_token_encrypted = ""
        connection.refresh_token_encrypted = None
        connection.token_expiry = None
        connection.history_id = None
        connection.last_synced_at = None

        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to disconnect Gmail",
        ) from exc

    return GmailDisconnectResponse(connected=False)