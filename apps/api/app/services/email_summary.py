"""Email thread summarization service."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread


class EmailSummaryError(RuntimeError):
    """Raised when an email thread cannot be summarized."""


class _HTMLTextExtractor(HTMLParser):
    """Extract readable text while ignoring style and script blocks."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() in {"style", "script"}:
            self._ignored_depth += 1

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.lower() in {"style", "script"}
            and self._ignored_depth > 0
        ):
            self._ignored_depth -= 1

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._ignored_depth > 0:
            return

        normalized = " ".join(data.split()).strip()

        if normalized:
            self._parts.append(normalized)

    def get_text(self) -> str:
        return " ".join(self._parts)


class EmailSummaryService:
    """Prepare email-thread content and generate a concise summary."""

    def summarize(
        self,
        thread: EmailThread,
        messages: list[EmailMessage],
    ) -> str:
        if not messages:
            raise EmailSummaryError(
                "The email thread does not contain any messages."
            )

        prepared_messages = [
            self._prepare_message(message)
            for message in messages
        ]

        prepared_messages = [
            message
            for message in prepared_messages
            if message
        ]

        if not prepared_messages:
            raise EmailSummaryError(
                "The email thread does not contain readable content."
            )

        subject = thread.subject or "No subject"

        # Placeholder summary.
        # Replace with AI provider integration later.
        return (
            f'Thread "{subject}" contains '
            f"{len(messages)} message"
            f"{'' if len(messages) == 1 else 's'}. "
            f"Participants: "
            f"{', '.join(thread.participant_emails or []) or 'unknown'}. "
            f"Latest content: {prepared_messages[-1][:500]}"
        )

    def _prepare_message(
        self,
        message: EmailMessage,
    ) -> str:
        sender = (
            message.sender_name
            or message.sender_email
            or "Unknown sender"
        )

        body = (
            message.text_body
            or self._html_to_text(message.html_body)
        )

        normalized_body = " ".join(
            body.split()
        ).strip()

        if not normalized_body:
            return ""

        return f"{sender}: {normalized_body}"

    @staticmethod
    def _html_to_text(
        html_body: str | None,
    ) -> str:
        if not html_body:
            return ""

        parser = _HTMLTextExtractor()

        try:
            parser.feed(html_body)
            parser.close()
        except Exception as exc:
            raise EmailSummaryError(
                "The email HTML could not be processed."
            ) from exc

        return unescape(parser.get_text())