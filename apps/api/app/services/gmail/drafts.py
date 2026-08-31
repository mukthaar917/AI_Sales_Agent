"""Gmail draft-reply service."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.services.gmail.client import GmailClient


class GmailDraftError(RuntimeError):
    """Raised when a Gmail draft cannot be created."""


@dataclass
class GmailDraftResult:
    """Result returned after creating a Gmail draft."""

    draft_id: str
    message_id: str | None = None


class GmailDraftService:
    """Create Gmail draft replies without sending them."""

    def __init__(
        self,
        gmail_client: GmailClient,
    ) -> None:
        self.gmail_client = gmail_client

    def create_thread_reply_draft(
        self,
        thread: EmailThread,
        latest_message: EmailMessage,
        subject: str,
        body: str,
        attachments: list[
            tuple[str, bytes, str]
        ] | None = None,
    ) -> GmailDraftResult:
        """Create a draft reply in the existing Gmail thread."""

        normalized_subject = self._reply_subject(
            subject or thread.subject
        )

        normalized_body = body.strip()

        if not normalized_body:
            raise GmailDraftError(
                "Reply body cannot be empty."
            )

        recipient = self._reply_recipient(
            latest_message
        )

        if not recipient:
            raise GmailDraftError(
                "A reply recipient could not be determined."
            )

        in_reply_to = (
            latest_message.internet_message_id
        )

        references = self._build_references(
            latest_message=latest_message,
        )

        try:
            result = self.gmail_client.create_draft(
                to=[recipient],
                subject=normalized_subject,
                body=normalized_body,
                thread_id=thread.provider_thread_id,
                in_reply_to=in_reply_to,
                references=references,
                attachments=attachments,
            )
        except Exception as exc:
            raise GmailDraftError(
                "Unable to create Gmail draft."
            ) from exc

        draft_id = str(
            result.get("draft_id", "")
            or result.get("id", "")
        ).strip()

        if not draft_id:
            raise GmailDraftError(
                "Gmail did not return a draft ID."
            )

        message_id_value = (
            result.get("message_id")
            or result.get("message", {}).get("id")
        )

        message_id = (
            str(message_id_value).strip()
            if message_id_value
            else None
        )

        return GmailDraftResult(
            draft_id=draft_id,
            message_id=message_id,
        )

    @staticmethod
    def _reply_recipient(
        latest_message: EmailMessage,
    ) -> str | None:
        """Choose the sender of the latest incoming message."""

        if (
            latest_message.direction == "incoming"
            and latest_message.sender_email
        ):
            return latest_message.sender_email.strip()

        return None

    @staticmethod
    def _reply_subject(
        subject: str | None,
    ) -> str:
        """Ensure the subject has one Re: prefix."""

        normalized = (
            subject or "No subject"
        ).strip()

        if normalized.lower().startswith("re:"):
            return normalized

        return f"Re: {normalized}"

    @staticmethod
    def _build_references(
        latest_message: EmailMessage,
    ) -> str | None:
        """Build References header for the reply."""

        parts: list[str] = []

        if latest_message.references_header:
            parts.extend(
                latest_message.references_header.split()
            )

        if latest_message.internet_message_id:
            message_id = (
                latest_message.internet_message_id.strip()
            )

            if message_id not in parts:
                parts.append(message_id)

        if not parts:
            return None

        return " ".join(parts)