"""Quotation requirement extraction from email threads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread


class QuotationExtractionError(RuntimeError):
    """Raised when quotation requirements cannot be extracted."""


@dataclass
class QuotationExtractionResult:
    """Structured requirements extracted from an email thread."""

    product: str | None
    quantity: int | None
    pricing_requested: bool
    availability_requested: bool
    delivery_requested: bool
    payment_terms_requested: bool
    confidence: float


class _HTMLTextExtractor(HTMLParser):
    """Extract readable text from an HTML email."""

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


class QuotationExtractionService:
    """Extract basic quotation requirements from an email thread."""

    PRODUCT_PATTERNS = (
        re.compile(
            r"\b(?:purchase|buy|order|need|require|want)"
            r"\s+(\d+)\s+"
            r"([a-zA-Z][a-zA-Z0-9 _-]{1,80}?)"
            r"(?=[.,;!?]|\s+(?:for|with|and|please)\b|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(\d+)\s+"
            r"([a-zA-Z][a-zA-Z0-9_-]{1,50})\b",
            re.IGNORECASE,
        ),
    )

    PRICING_TERMS = (
        "quotation",
        "quote",
        "pricing",
        "price",
        "cost",
    )

    AVAILABILITY_TERMS = (
        "availability",
        "available",
        "in stock",
        "stock availability",
    )

    DELIVERY_TERMS = (
        "delivery",
        "delivery time",
        "lead time",
        "shipping",
    )

    PAYMENT_TERMS = (
        "payment terms",
        "payment term",
        "payment conditions",
        "credit terms",
    )

    def extract(
        self,
        thread: EmailThread,
        messages: list[EmailMessage],
    ) -> QuotationExtractionResult:
        """Extract quotation requirements from a synchronized thread."""

        if not messages:
            raise QuotationExtractionError(
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

        combined_text = " ".join(
            part
            for part in text_parts
            if part
        )

        combined_text = " ".join(
            combined_text.split()
        ).strip()

        if not combined_text:
            raise QuotationExtractionError(
                "The email thread does not contain readable content."
            )

        product, quantity = self._extract_product_and_quantity(
            combined_text
        )

        normalized_text = combined_text.lower()

        pricing_requested = self._contains_any(
            normalized_text,
            self.PRICING_TERMS,
        )

        availability_requested = self._contains_any(
            normalized_text,
            self.AVAILABILITY_TERMS,
        )

        delivery_requested = self._contains_any(
            normalized_text,
            self.DELIVERY_TERMS,
        )

        payment_terms_requested = self._contains_any(
            normalized_text,
            self.PAYMENT_TERMS,
        )

        confidence = self._calculate_confidence(
            product=product,
            quantity=quantity,
            pricing_requested=pricing_requested,
            availability_requested=availability_requested,
            delivery_requested=delivery_requested,
            payment_terms_requested=payment_terms_requested,
        )

        return QuotationExtractionResult(
            product=product,
            quantity=quantity,
            pricing_requested=pricing_requested,
            availability_requested=availability_requested,
            delivery_requested=delivery_requested,
            payment_terms_requested=payment_terms_requested,
            confidence=confidence,
        )

    def _extract_product_and_quantity(
        self,
        text: str,
    ) -> tuple[str | None, int | None]:
        for pattern in self.PRODUCT_PATTERNS:
            match = pattern.search(text)

            if match is None:
                continue

            try:
                quantity = int(match.group(1))
            except (TypeError, ValueError):
                continue

            product = self._normalize_product(
                match.group(2)
            )

            if not product:
                continue

            return product, quantity

        return None, None

    @staticmethod
    def _normalize_product(
        value: str,
    ) -> str:
        product = " ".join(
            value.split()
        ).strip(" ,.;:-")

        return product.lower()

    @staticmethod
    def _contains_any(
        text: str,
        terms: tuple[str, ...],
    ) -> bool:
        return any(
            term in text
            for term in terms
        )

    @staticmethod
    def _calculate_confidence(
        product: str | None,
        quantity: int | None,
        pricing_requested: bool,
        availability_requested: bool,
        delivery_requested: bool,
        payment_terms_requested: bool,
    ) -> float:
        score = 0.0

        if product:
            score += 0.25

        if quantity is not None:
            score += 0.25

        if pricing_requested:
            score += 0.20

        if availability_requested:
            score += 0.10

        if delivery_requested:
            score += 0.10

        if payment_terms_requested:
            score += 0.10

        return round(
            min(score, 1.0),
            2,
        )

    def _prepare_message(
        self,
        message: EmailMessage,
    ) -> str:
        body = (
            message.text_body
            or self._html_to_text(message.html_body)
        )

        return " ".join(
            body.split()
        ).strip()

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
            raise QuotationExtractionError(
                "The email HTML could not be processed."
            ) from exc

        return unescape(
            parser.get_text()
        )