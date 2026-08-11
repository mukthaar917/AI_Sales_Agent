from __future__ import annotations

import base64
from email.message import EmailMessage as MIMEEmailMessage
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
            raise ValueError(
                "Gmail access token is required."
            )

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

            messages = response.get(
                "messages",
                [],
            )

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
            raise ValueError(
                "Gmail message ID is required."
            )

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
            raise ValueError(
                "Gmail thread ID is required."
            )

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

    def create_draft(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        thread_id: str,
        in_reply_to: str | None = None,
        references: str | None = None,
        attachments: list[
            tuple[str, bytes, str]
        ] | None = None,
    ) -> dict[str, Any]:
        """
        Create a Gmail draft in an existing thread.

        attachments contains:
            (filename, content_bytes, mime_type)
        """

        recipients = [
            address.strip()
            for address in to
            if address.strip()
        ]

        if not recipients:
            raise ValueError(
                "At least one recipient is required."
            )

        normalized_subject = subject.strip()
        normalized_body = body.strip()
        normalized_thread_id = thread_id.strip()

        if not normalized_subject:
            raise ValueError(
                "Draft subject is required."
            )

        if not normalized_body:
            raise ValueError(
                "Draft body is required."
            )

        if not normalized_thread_id:
            raise ValueError(
                "Gmail thread ID is required."
            )

        message = MIMEEmailMessage()

        message["To"] = ", ".join(recipients)
        message["Subject"] = normalized_subject

        if in_reply_to:
            normalized_in_reply_to = (
                in_reply_to.strip()
            )

            if normalized_in_reply_to:
                message["In-Reply-To"] = (
                    normalized_in_reply_to
                )

        if references:
            normalized_references = (
                references.strip()
            )

            if normalized_references:
                message["References"] = (
                    normalized_references
                )

        message.set_content(
            normalized_body
        )

        for attachment in attachments or []:
            filename, content, mime_type = attachment

            normalized_filename = filename.strip()
            normalized_mime_type = mime_type.strip().lower()

            if not normalized_filename:
                raise ValueError(
                    "Attachment filename is required."
                )

            if not isinstance(content, bytes):
                raise ValueError(
                    "Attachment content must be bytes."
                )

            if not content:
                raise ValueError(
                    "Attachment content cannot be empty."
                )

            if "/" not in normalized_mime_type:
                raise ValueError(
                    "Attachment MIME type is invalid."
                )

            maintype, subtype = (
                normalized_mime_type.split("/", 1)
            )

            if not maintype or not subtype:
                raise ValueError(
                    "Attachment MIME type is invalid."
                )

            message.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=normalized_filename,
            )

        raw_message = (
            base64.urlsafe_b64encode(
                message.as_bytes()
            )
            .decode("utf-8")
        )

        request_body = {
            "message": {
                "raw": raw_message,
                "threadId": normalized_thread_id,
            }
        }

        try:
            response = (
                self._service.users()
                .drafts()
                .create(
                    userId="me",
                    body=request_body,
                )
                .execute()
            )

            if not isinstance(response, dict):
                raise GmailClientError(
                    "Gmail returned an invalid draft response."
                )

            return response

        except GmailClientError:
            raise

        except Exception:
            raise GmailClientError(
                "Unable to create Gmail draft."
            ) from None