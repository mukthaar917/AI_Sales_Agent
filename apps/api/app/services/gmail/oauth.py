"""Gmail OAuth service.

This module handles Google OAuth authorization, authorization-code exchange,
access-token refresh, and Gmail profile retrieval.

It does not store credentials or write to the database. Token encryption and
GmailConnection persistence should be handled by a higher-level service or API
endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings


GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailOAuthError(Exception):
    """Raised when a Gmail OAuth operation fails safely."""


class GmailOAuthService:
    """Service for Gmail OAuth and Gmail profile operations."""

    def __init__(self) -> None:
        self.client_id = settings.google_client_id.strip()
        self.client_secret = settings.google_client_secret.strip()
        self.redirect_uri = settings.google_redirect_uri.strip()
        self.scopes = self._normalize_scopes(settings.gmail_scopes)

    def build_authorization_url(self) -> tuple[str, str]:
        """Build Google's OAuth authorization URL.

        Returns:
            A tuple containing the authorization URL and generated OAuth state.

        Raises:
            GmailOAuthError: If OAuth configuration is invalid or URL creation
                fails.
        """
        try:
            flow = self._create_flow()

            authorization_url, state = flow.authorization_url(
                access_type="offline",
                prompt="consent",
                include_granted_scopes="true",
            )

            return authorization_url, state
        except GmailOAuthError:
            raise
        except Exception as exc:
            raise GmailOAuthError(
                "Unable to create Gmail authorization URL."
            ) from exc

    def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange an OAuth authorization code for Google credentials.

        Args:
            code: Authorization code returned by Google.

        Returns:
            Normalized token information containing access token, refresh token,
            expiry, and scopes.

        Raises:
            ValueError: If the authorization code is empty.
            GmailOAuthError: If Google rejects the code or token exchange fails.
        """
        normalized_code = code.strip()

        if not normalized_code:
            raise ValueError("Authorization code is required.")

        try:
            flow = self._create_flow()
            flow.fetch_token(code=normalized_code)

            credentials = flow.credentials

            if not credentials.token:
                raise GmailOAuthError(
                    "Google did not return a Gmail access token."
                )

            return self._normalize_credentials(credentials)
        except GmailOAuthError:
            raise
        except Exception as exc:
            raise GmailOAuthError(
                "Unable to exchange Gmail authorization code for tokens."
            ) from exc

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh an expired Gmail access token.

        Args:
            refresh_token: Stored Google OAuth refresh token.

        Returns:
            Normalized refreshed token information.

        Raises:
            ValueError: If the refresh token is empty.
            GmailOAuthError: If refreshing the token fails.
        """
        normalized_refresh_token = refresh_token.strip()

        if not normalized_refresh_token:
            raise ValueError("Refresh token is required.")

        try:
            self._validate_configuration()

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

            # Some mocked or provider-generated credential objects may not
            # retain the refresh token after refresh. Preserve the supplied
            # stored token in that case.
            if not result["refresh_token"]:
                result["refresh_token"] = normalized_refresh_token

            return result
        except GmailOAuthError:
            raise
        except Exception as exc:
            raise GmailOAuthError(
                "Unable to refresh Gmail access token."
            ) from exc

    def fetch_gmail_profile(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        """Retrieve the authenticated user's Gmail profile.

        Args:
            access_token: Valid Google OAuth access token.

        Returns:
            Normalized Gmail profile information.

        Raises:
            ValueError: If the access token is empty.
            GmailOAuthError: If profile retrieval fails or the response does
                not contain an email address.
        """
        normalized_access_token = access_token.strip()

        if not normalized_access_token:
            raise ValueError("Access token is required.")

        try:
            credentials = Credentials(token=normalized_access_token)

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
        except Exception as exc:
            raise GmailOAuthError(
                "Unable to retrieve Gmail profile."
            ) from exc

    def _create_flow(self) -> Flow:
        """Create and configure a Google OAuth flow."""
        self._validate_configuration()

        flow = Flow.from_client_config(
            self._client_config(),
            scopes=self.scopes,
        )
        flow.redirect_uri = self.redirect_uri

        return flow

    def _client_config(self) -> dict[str, dict[str, Any]]:
        """Build Google OAuth client configuration from application settings."""
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
        """Validate required Gmail OAuth configuration."""
        missing_settings: list[str] = []

        if not self.client_id:
            missing_settings.append("GOOGLE_CLIENT_ID")

        if not self.client_secret:
            missing_settings.append("GOOGLE_CLIENT_SECRET")

        if not self.redirect_uri:
            missing_settings.append("GOOGLE_REDIRECT_URI")

        if not self.scopes:
            missing_settings.append("GMAIL_SCOPES")

        if missing_settings:
            names = ", ".join(missing_settings)
            raise GmailOAuthError(
                f"Gmail OAuth configuration is incomplete: {names}."
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
    def _normalize_scopes(value: str | list[str] | tuple[str, ...]) -> list[str]:
        """Normalize configured Gmail scopes into a list."""
        if isinstance(value, str):
            # Supports either whitespace-separated or comma-separated scopes.
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