"""Gmail OAuth service.

Handles:

- Google OAuth authorization URL generation
- Authorization-code exchange
- Access-token refresh
- Gmail profile retrieval

This service does not write credentials to the database. Credential encryption
and GmailConnection persistence should be handled by a higher-level service or
API endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings


GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailOAuthError(Exception):
    """Raised when a Gmail OAuth operation cannot be completed safely."""


class GmailOAuthService:
    """Provide Gmail OAuth and Gmail profile operations."""

    def __init__(self) -> None:
        self.client_id = settings.google_client_id.strip()
        self.client_secret = settings.google_client_secret.strip()
        self.redirect_uri = settings.google_redirect_uri.strip()
        self.scopes = self._normalize_scopes(settings.gmail_scopes)

    def build_authorization_url(self) -> tuple[str, str]:
        """Create a Google OAuth authorization URL and state value."""

        self._validate_configuration()

        try:
            flow = self._create_flow()

            authorization_url, state = flow.authorization_url(
                access_type="offline",
                prompt="consent",
                include_granted_scopes="true",
            )

            if not authorization_url:
                raise GmailOAuthError(
                    "Google OAuth did not produce an authorization URL."
                )

            if not state:
                raise GmailOAuthError(
                    "Google OAuth did not produce a state value."
                )

            return authorization_url, state

        except GmailOAuthError:
            raise
        except Exception:
            raise GmailOAuthError(
                "Unable to create Gmail authorization URL."
            ) from None

    def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange a Google authorization code for OAuth credentials."""

        normalized_code = code.strip()

        if not normalized_code:
            raise ValueError("Authorization code is required.")

        self._validate_configuration()

        try:
            flow = self._create_flow()

            flow.fetch_token(
                code=normalized_code,
            )

            credentials = flow.credentials

            if not credentials.token:
                raise GmailOAuthError(
                    "Google did not return a Gmail access token."
                )

            return self._normalize_credentials(credentials)

        except GmailOAuthError:
            raise
        except Exception:
            raise GmailOAuthError(
                "Unable to exchange Gmail authorization code for tokens."
            ) from None

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh a Google access token using a stored refresh token."""

        normalized_refresh_token = refresh_token.strip()

        if not normalized_refresh_token:
            raise ValueError("Refresh token is required.")

        self._validate_configuration()

        try:
            credentials = Credentials(
                token=None,
                refresh_token=normalized_refresh_token,
                token_uri=GOOGLE_TOKEN_URI,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )

            credentials.refresh(Request())

            if not credentials.token:
                raise GmailOAuthError(
                    "Google did not return a refreshed Gmail access token."
                )

            result = self._normalize_credentials(credentials)

            if not result["refresh_token"]:
                result["refresh_token"] = normalized_refresh_token

            return result

        except GmailOAuthError:
            raise
        except Exception:
            raise GmailOAuthError(
                "Unable to refresh Gmail access token."
            ) from None

    def fetch_gmail_profile(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        """Retrieve the authenticated Google account's Gmail profile."""

        normalized_access_token = access_token.strip()

        if not normalized_access_token:
            raise ValueError("Access token is required.")

        try:
            credentials = Credentials(
                token=normalized_access_token,
                scopes=self.scopes,
            )

            gmail = build(
                "gmail",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )

            profile = (
                gmail.users()
                .getProfile(userId="me")
                .execute()
            )

            email_address = profile.get("emailAddress")

            if not email_address:
                raise GmailOAuthError(
                    "Gmail profile did not contain an email address."
                )

            return {
                "email_address": email_address,
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId"),
            }

        except GmailOAuthError:
            raise
        except Exception:
            raise GmailOAuthError(
                "Unable to retrieve Gmail profile."
            ) from None

    def _create_flow(self) -> Flow:
        """Create a configured Google OAuth flow."""

        self._validate_configuration()

        return Flow.from_client_config(
            client_config=self._client_config(),
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            autogenerate_code_verifier=False,
        )

    def _client_config(self) -> dict[str, dict[str, Any]]:
        """Return Google OAuth client configuration."""

        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
                "redirect_uris": [self.redirect_uri],
            }
        }

    def _validate_configuration(self) -> None:
        """Validate all required Gmail OAuth settings."""

        errors: list[str] = []

        if not self.client_id:
            errors.append("GOOGLE_CLIENT_ID")
        elif self._looks_like_placeholder(self.client_id):
            errors.append("GOOGLE_CLIENT_ID contains a placeholder")

        if not self.client_secret:
            errors.append("GOOGLE_CLIENT_SECRET")
        elif self._looks_like_placeholder(self.client_secret):
            errors.append(
                "GOOGLE_CLIENT_SECRET contains a placeholder"
            )

        if not self.redirect_uri:
            errors.append("GOOGLE_REDIRECT_URI")

        if not self.scopes:
            errors.append("GMAIL_SCOPES")

        if errors:
            raise GmailOAuthError(
                "Gmail OAuth configuration is incomplete: "
                + ", ".join(errors)
                + "."
            )

    @staticmethod
    def _normalize_credentials(
        credentials: Credentials,
    ) -> dict[str, Any]:
        """Convert Google credentials into an application-safe dictionary."""

        expiry: datetime | None = credentials.expiry
        credential_scopes = credentials.scopes or []

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": expiry,
            "scopes": list(credential_scopes),
        }

    @staticmethod
    def _normalize_scopes(
        value: str | list[str] | tuple[str, ...],
    ) -> list[str]:
        """Normalize whitespace- or comma-separated Gmail scopes."""

        if isinstance(value, str):
            return [
                scope.strip()
                for scope in value.replace(",", " ").split()
                if scope.strip()
            ]

        return [
            str(scope).strip()
            for scope in value
            if str(scope).strip()
        ]

    @staticmethod
    def _looks_like_placeholder(value: str) -> bool:
        """Return True when a setting appears to contain placeholder text."""

        normalized = value.strip().upper()

        placeholder_markers = (
            "YOUR_REAL_",
            "PASTE_",
            "REPLACE_",
            "YOUR_CLIENT_",
            "YOUR_ACTUAL_",
            "EXAMPLE",
        )

        return any(
            marker in normalized
            for marker in placeholder_markers
        )