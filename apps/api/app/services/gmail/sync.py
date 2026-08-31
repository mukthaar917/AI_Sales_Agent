from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import getaddresses, parseaddr
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.gmail_connection import GmailConnection
from app.services.gmail.client import GmailClient


class GmailSyncError(RuntimeError):
    """Raised when Gmail synchronization cannot be completed safely."""


class GmailSyncService:
    """Synchronize Gmail inbox messages into the local database."""

    def __init__(
        self,
        db: Session,
        gmail_client: GmailClient,
        connection: GmailConnection,
    ) -> None:
        self.db = db
        self.gmail_client = gmail_client
        self.connection = connection

    def sync_inbox(
        self,
        max_results: int = 25,
    ) -> dict[str, int]:
        """Synchronize Gmail inbox messages."""

        statistics = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }

        try:
            message_references = self.gmail_client.list_messages(
                max_results=max_results
            )
        except Exception:
            raise GmailSyncError(
                "Unable to synchronize the Gmail inbox."
            ) from None

        statistics["fetched"] = len(message_references)

        for message_reference in message_references:
            message_id = str(
                message_reference.get("id", "")
            ).strip()

            if not message_id:
                statistics["failed"] += 1
                continue

            try:
                gmail_message = self.gmail_client.get_message(
                    message_id
                )

                existing_message = self._find_message(
                    provider_message_id=message_id
                )

                thread, thread_created, thread_updated = (
                    self._upsert_thread(gmail_message)
                )

                if existing_message is not None:
                    statistics["skipped"] += 1

                    if thread_updated:
                        statistics["updated"] += 1

                    continue

                self._create_message(
                    gmail_message=gmail_message,
                    thread=thread,
                )

                statistics["created"] += 1

                if thread_updated and not thread_created:
                    statistics["updated"] += 1

            except Exception:
                statistics["failed"] += 1

        try:
            self.connection.last_synced_at = datetime.now(
                timezone.utc
            )

            self.db.add(self.connection)
            self.db.commit()

        except Exception:
            self.db.rollback()

            raise GmailSyncError(
                "Unable to save Gmail synchronization results."
            ) from None

        return statistics

    def _find_message(
        self,
        provider_message_id: str,
    ) -> EmailMessage | None:
        statement = select(EmailMessage).where(
            EmailMessage.gmail_connection_id
            == self.connection.id,
            EmailMessage.provider_message_id
            == provider_message_id,
        )

        return self.db.scalar(statement)

    def _upsert_thread(
        self,
        gmail_message: dict[str, Any],
    ) -> tuple[EmailThread, bool, bool]:
        provider_thread_id = str(
            gmail_message.get("threadId", "")
        ).strip()

        if not provider_thread_id:
            raise GmailSyncError(
                "Gmail message does not contain a thread ID."
            )

        headers = self._header_map(gmail_message)
        labels = set(gmail_message.get("labelIds", []))

        subject = headers.get("subject")
        snippet = gmail_message.get("snippet")
        message_time = self._message_datetime(gmail_message)

        participant_emails = self._unique_addresses(
            headers.get("from"),
            headers.get("to"),
            headers.get("cc"),
        )

        statement = select(EmailThread).where(
            EmailThread.gmail_connection_id
            == self.connection.id,
            EmailThread.provider_thread_id
            == provider_thread_id,
        )

        thread = self.db.scalar(statement)

        if thread is None:
            thread = EmailThread(
                organization_id=self.connection.organization_id,
                gmail_connection_id=self.connection.id,
                provider_thread_id=provider_thread_id,
                subject=subject,
                snippet=snippet,
                participant_emails=participant_emails,
                last_message_at=message_time,
                unread="UNREAD" in labels,
            )

            self.db.add(thread)
            self.db.flush()

            return thread, True, False

        changed = False

        updates = {
            "subject": subject,
            "snippet": snippet,
            "participant_emails": participant_emails,
            "unread": "UNREAD" in labels,
        }

        for attribute, value in updates.items():
            if getattr(thread, attribute) != value:
                setattr(thread, attribute, value)
                changed = True

        if (
            message_time is not None
            and (
                thread.last_message_at is None
                or message_time > thread.last_message_at
            )
        ):
            thread.last_message_at = message_time
            changed = True

        if changed:
            self.db.add(thread)

        return thread, False, changed

    def _create_message(
        self,
        gmail_message: dict[str, Any],
        thread: EmailThread,
    ) -> EmailMessage:
        provider_message_id = str(
            gmail_message.get("id", "")
        ).strip()

        provider_thread_id = str(
            gmail_message.get("threadId", "")
        ).strip()

        if not provider_message_id:
            raise GmailSyncError(
                "Gmail message does not contain a message ID."
            )

        headers = self._header_map(gmail_message)
        labels = set(gmail_message.get("labelIds", []))

        sender_name, sender_email = parseaddr(
            headers.get("from", "")
        )

        recipient_emails = self._parse_addresses(
            headers.get("to")
        )

        cc_emails = self._parse_addresses(
            headers.get("cc")
        )

        text_body, html_body = self._extract_bodies(
            gmail_message.get("payload", {})
        )

        sender_normalized = sender_email.strip().lower()
        connected_address = (
            self.connection.gmail_address.strip().lower()
        )

        direction = (
            "outgoing"
            if sender_normalized == connected_address
            else "incoming"
        )

        message_time = self._message_datetime(
            gmail_message
        )

        message = EmailMessage(
            organization_id=self.connection.organization_id,
            gmail_connection_id=self.connection.id,
            thread_id=thread.id,
            provider_message_id=provider_message_id,
            provider_thread_id=provider_thread_id,
            internet_message_id=headers.get("message-id"),
            in_reply_to=headers.get("in-reply-to"),
            references_header=headers.get("references"),
            sender_name=sender_name or None,
            sender_email=sender_email or None,
            recipient_emails=recipient_emails,
            cc_emails=cc_emails,
            subject=headers.get("subject"),
            text_body=text_body,
            html_body=html_body,
            received_at=(
                message_time
                if direction == "incoming"
                else None
            ),
            sent_at=(
                message_time
                if direction == "outgoing"
                else None
            ),
            direction=direction,
            unread="UNREAD" in labels,
            has_attachments=self._has_attachments(
                gmail_message.get("payload", {})
            ),
            raw_headers=headers,
        )

        self.db.add(message)
        self.db.flush()

        return message

    @staticmethod
    def _header_map(
        gmail_message: dict[str, Any],
    ) -> dict[str, str]:
        payload = gmail_message.get("payload", {})
        raw_headers = payload.get("headers", [])

        result: dict[str, str] = {}

        for header in raw_headers:
            name = str(header.get("name", "")).strip().lower()
            value = str(header.get("value", "")).strip()

            if name:
                result[name] = value

        return result

    @staticmethod
    def _message_datetime(
        gmail_message: dict[str, Any],
    ) -> datetime | None:
        internal_date = gmail_message.get("internalDate")

        if internal_date is None:
            return None

        try:
            milliseconds = int(internal_date)

            return datetime.fromtimestamp(
                milliseconds / 1000,
                tz=timezone.utc,
            )
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _parse_addresses(
        value: str | None,
    ) -> list[str]:
        if not value:
            return []

        return [
            address.strip().lower()
            for _, address in getaddresses([value])
            if address.strip()
        ]

    @classmethod
    def _unique_addresses(
        cls,
        *values: str | None,
    ) -> list[str]:
        addresses: list[str] = []

        for value in values:
            for address in cls._parse_addresses(value):
                if address not in addresses:
                    addresses.append(address)

        return addresses

    @classmethod
    def _extract_bodies(
        cls,
        payload: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        text_parts: list[str] = []
        html_parts: list[str] = []

        cls._collect_body_parts(
            payload,
            text_parts=text_parts,
            html_parts=html_parts,
        )

        text_body = "\n".join(
            part for part in text_parts if part
        ).strip()

        html_body = "\n".join(
            part for part in html_parts if part
        ).strip()

        return (
            text_body or None,
            html_body or None,
        )

    @classmethod
    def _collect_body_parts(
        cls,
        part: dict[str, Any],
        text_parts: list[str],
        html_parts: list[str],
    ) -> None:
        mime_type = str(
            part.get("mimeType", "")
        ).lower()

        body_data = (
            part.get("body", {})
            .get("data")
        )

        if body_data:
            decoded = cls._decode_base64url(body_data)

            if mime_type == "text/plain":
                text_parts.append(decoded)
            elif mime_type == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts", []) or []:
            cls._collect_body_parts(
                child,
                text_parts=text_parts,
                html_parts=html_parts,
            )

    @staticmethod
    def _decode_base64url(value: str) -> str:
        try:
            padded = value + "=" * (-len(value) % 4)

            return base64.urlsafe_b64decode(
                padded.encode("utf-8")
            ).decode(
                "utf-8",
                errors="replace",
            )
        except (ValueError, TypeError):
            return ""

    @classmethod
    def _has_attachments(
        cls,
        payload: dict[str, Any],
    ) -> bool:
        filename = str(
            payload.get("filename", "")
        ).strip()

        attachment_id = (
            payload.get("body", {})
            .get("attachmentId")
        )

        if filename or attachment_id:
            return True

        return any(
            cls._has_attachments(child)
            for child in payload.get("parts", []) or []
        )