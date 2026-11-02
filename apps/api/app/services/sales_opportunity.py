"""Sales opportunity detection service."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread


class SalesOpportunityError(RuntimeError):
    """Raised when a thread cannot be classified."""


@dataclass
class SalesOpportunityResult:
    """Structured sales-opportunity classification result."""

    classification: str
    confidence: float
    reason: str


class _HTMLTextExtractor(HTMLParser):
    """Extract readable email text."""

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


class SalesOpportunityService:
    """Classify whether an email thread represents a sales opportunity."""

    SALES_KEYWORDS = {
        "quote",
        "quotation",
        "price",
        "pricing",
        "cost",
        "buy",
        "purchase",
        "order",
        "requirement",
        "requirements",
        "quantity",
        "qty",
        "product",
        "products",
        "proposal",
        "availability",
        "delivery",
        "lead time",
        "rfq",
        "request for quotation",
    }

    NON_SALES_KEYWORDS = {
        "sign-in",
        "security alert",
        "password",
        "verification",
        "subscription",
        "newsletter",
        "account security",
        "login",
    }

    def detect(
        self,
        thread: EmailThread,
        messages: list[EmailMessage],
    ) -> SalesOpportunityResult:
        if not messages:
            raise SalesOpportunityError(
                "The email thread does not contain any messages."
            )

        text_parts = [
            thread.subject or "",
            thread.snippet or "",
        ]

        for message in messages:
            text_parts.append(
                self._prepare_message(message)
            )

        combined_text = " ".join(text_parts).lower()

        if not combined_text.strip():
            return SalesOpportunityResult(
                classification="unknown",
                confidence=0.0,
                reason="The thread does not contain readable content.",
            )

        sales_matches = [
            keyword
            for keyword in self.SALES_KEYWORDS
            if keyword in combined_text
        ]

        non_sales_matches = [
            keyword
            for keyword in self.NON_SALES_KEYWORDS
            if keyword in combined_text
        ]

        if sales_matches and len(sales_matches) > len(non_sales_matches):
            confidence = min(
                0.55 + (0.08 * len(sales_matches)),
                0.95,
            )

            return SalesOpportunityResult(
                classification="sales_opportunity",
                confidence=round(confidence, 2),
                reason=(
                    "Sales-related terms detected: "
                    + ", ".join(sorted(sales_matches)[:6])
                    + "."
                ),
            )

        if non_sales_matches and not sales_matches:
            confidence = min(
                0.65 + (0.05 * len(non_sales_matches)),
                0.95,
            )

            return SalesOpportunityResult(
                classification="non_sales",
                confidence=round(confidence, 2),
                reason=(
                    "Non-sales notification terms detected: "
                    + ", ".join(sorted(non_sales_matches)[:6])
                    + "."
                ),
            )

        return SalesOpportunityResult(
            classification="unknown",
            confidence=0.5,
            reason=(
                "The thread does not contain enough clear "
                "sales or non-sales indicators."
            ),
        )

    def _prepare_message(
        self,
        message: EmailMessage,
    ) -> str:
        body = (
            message.text_body
            or self._html_to_text(message.html_body)
        )

        return " ".join(body.split()).strip()

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
            raise SalesOpportunityError(
                "The email HTML could not be processed."
            ) from exc

        return unescape(parser.get_text())