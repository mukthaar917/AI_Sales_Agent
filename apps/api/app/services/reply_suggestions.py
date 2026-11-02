"""Email reply suggestion service."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.schemas.email import ReplySuggestion


class ReplySuggestionError(RuntimeError):
    """Raised when reply suggestions cannot be generated."""


class _HTMLTextExtractor(HTMLParser):
    """Extract readable text while ignoring non-content HTML."""

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


class ReplySuggestionService:
    """Generate reviewable reply suggestions for an email thread."""

    def generate(
        self,
        thread: EmailThread,
        messages: list[EmailMessage],
    ) -> list[ReplySuggestion]:
        if not messages:
            raise ReplySuggestionError(
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
            raise ReplySuggestionError(
                "The email thread does not contain readable content."
            )

        latest_message = prepared_messages[-1]
        subject = self._reply_subject(thread.subject)

        # Temporary deterministic suggestions.
        # Replace this block with the configured AI provider later.
        return [
            ReplySuggestion(
                subject=subject,
                body=(
                    "Thank you for your email. "
                    "We have reviewed your message and will follow up "
                    "with the relevant details shortly."
                ),
            ),
            ReplySuggestion(
                subject=subject,
                body=(
                    "Thank you for reaching out. "
                    f"We noted the following from your latest message: "
                    f"{latest_message[:300]} "
                    "Please let us know if there is anything else "
                    "you would like us to consider."
                ),
            ),
        ]

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
    def _reply_subject(
        subject: str | None,
    ) -> str:
        normalized = (subject or "No subject").strip()

        if normalized.lower().startswith("re:"):
            return normalized

        return f"Re: {normalized}"

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
            raise ReplySuggestionError(
                "The email HTML could not be processed."
            ) from exc

        return unescape(parser.get_text())