"""Grounded AI email reply suggestion service."""

from __future__ import annotations

import uuid
from html import unescape
from html.parser import HTMLParser

from sqlalchemy.orm import Session

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.schemas.email import ReplySuggestion
from app.services.rag_answer_service import (
    RAGAnswerError,
    RAGAnswerService,
)


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

        normalized = " ".join(
            data.split()
        ).strip()

        if normalized:
            self._parts.append(normalized)

    def get_text(self) -> str:
        return " ".join(self._parts)


class ReplySuggestionService:
    """Generate a grounded, reviewable reply for an email thread."""

    def __init__(self) -> None:
        self.rag = RAGAnswerService()

    def generate(
        self,
        *,
        db: Session,
        organization_id: uuid.UUID,
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

        try:
            rag_result = self.rag.answer(
                db,
                organization_id=organization_id,
                question=latest_message,
                limit=3,
            )

        except RAGAnswerError as exc:
            raise ReplySuggestionError(
                "Unable to generate a grounded reply suggestion."
            ) from exc

        subject = self._reply_subject(
            thread.subject
        )

        # No relevant approved knowledge was retrieved.
        #
        # In this case there is nothing grounded that can safely
        # be included in the customer reply, so require human review.
        if (
            rag_result.insufficient_knowledge
            and not rag_result.sources
        ):
            body = self._build_insufficient_knowledge_reply()

            return [
                ReplySuggestion(
                    subject=subject,
                    body=body,
                )
            ]

        # Relevant approved knowledge was found.
        #
        # This covers:
        #
        # 1. Fully supported requests
        # 2. Partially supported requests
        #
        # For partially supported requests, RAGAnswerService has
        # already been instructed to answer supported facts and
        # clearly flag unsupported facts for confirmation.
        body = self._build_reply_body(
            rag_result.answer
        )

        return [
            ReplySuggestion(
                subject=subject,
                body=body,
            )
        ]

    @staticmethod
    def _build_reply_body(
        grounded_answer: str,
    ) -> str:
        """Return the grounded AI reply without duplicating content."""

        answer = grounded_answer.strip()

        if not answer:
            raise ReplySuggestionError(
                "The grounded AI answer was empty."
            )

        return answer

    @staticmethod
    def _build_insufficient_knowledge_reply() -> str:
        """Return the safe fallback when no grounded knowledge exists."""

        return (
            "Thank you for your email.\n\n"
            "We have reviewed your request, but the approved "
            "company knowledge currently available does not "
            "contain enough information for us to provide a "
            "reliable response.\n\n"
            "Your request requires human review before we can "
            "confirm the requested details."
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
            or self._html_to_text(
                message.html_body
            )
        )

        normalized_body = " ".join(
            body.split()
        ).strip()

        if not normalized_body:
            return ""

        return (
            f"Customer: {sender}\n"
            f"Message: {normalized_body}"
        )

    @staticmethod
    def _reply_subject(
        subject: str | None,
    ) -> str:
        """Normalize the original subject and add one Re: prefix."""

        normalized = (
            subject or "No subject"
        ).strip()

        # Some synchronized emails may contain a redundant
        # "Subject:" prefix in the stored subject.
        if normalized.lower().startswith(
            "subject:"
        ):
            normalized = normalized[
                len("subject:")
            :].strip()

        # Avoid producing "Re: Re: ..."
        if normalized.lower().startswith(
            "re:"
        ):
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

        return unescape(
            parser.get_text()
        )