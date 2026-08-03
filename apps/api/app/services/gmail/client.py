from __future__ import annotations

from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GmailClientError(RuntimeError):
    """Raised when a Gmail API operation fails safely."""


class GmailClient:
    """Small wrapper around the Gmail API client."""

    def __init__(
        self,
        access_token: str,
        scopes: list[str] | None = None,
    ) -> None:
        normalized_token = access_token.strip()

        if not normalized_token:
            raise ValueError("Gmail access token is required.")

        credentials = Credentials(
            token=normalized_token,
            scopes=scopes or None,
        )

        try:
            self._service = build(
                "gmail",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception:
            raise GmailClientError(
                "Unable to initialize the Gmail API client."
            ) from None

    def list_messages(
        self,
        max_results: int = 25,
    ) -> list[dict[str, Any]]:
        """Return inbox message identifiers."""

        if max_results < 1 or max_results > 500:
            raise ValueError(
                "max_results must be between 1 and 500."
            )

        try:
            response = (
                self._service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=["INBOX"],
                    maxResults=max_results,
                )
                .execute()
            )

            messages = response.get("messages", [])

            if not isinstance(messages, list):
                return []

            return messages

        except Exception:
            raise GmailClientError(
                "Unable to list Gmail messages."
            ) from None

    def get_message(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        """Return a complete Gmail message."""

        normalized_id = message_id.strip()

        if not normalized_id:
            raise ValueError("Gmail message ID is required.")

        try:
            return (
                self._service.users()
                .messages()
                .get(
                    userId="me",
                    id=normalized_id,
                    format="full",
                )
                .execute()
            )
        except Exception:
            raise GmailClientError(
                "Unable to retrieve the Gmail message."
            ) from None

    def get_thread(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        """Return a complete Gmail thread."""

        normalized_id = thread_id.strip()

        if not normalized_id:
            raise ValueError("Gmail thread ID is required.")

        try:
            return (
                self._service.users()
                .threads()
                .get(
                    userId="me",
                    id=normalized_id,
                    format="full",
                )
                .execute()
            )
        except Exception:
            raise GmailClientError(
                "Unable to retrieve the Gmail thread."
            ) from None