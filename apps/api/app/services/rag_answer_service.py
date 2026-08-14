"""Grounded RAG answer generation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.ai_provider import (
    AIProviderError,
    AIProviderService,
)
from app.services.knowledge_search_service import (
    search_knowledge,
)


class RAGAnswerError(RuntimeError):
    """Raised when a grounded answer cannot be generated."""


@dataclass
class RAGSource:
    """One source supporting a grounded answer."""

    document_id: uuid.UUID
    chunk_id: uuid.UUID
    filename: str
    page: int | None
    score: float


@dataclass
class RAGAnswerResult:
    """Grounded answer with supporting knowledge sources."""

    answer: str
    sources: list[RAGSource]
    insufficient_knowledge: bool


class RAGAnswerService:
    """Generate answers using organization-scoped company knowledge."""

    def __init__(self) -> None:
        self.ai = AIProviderService()

    def answer(
        self,
        db: Session,
        *,
        organization_id: uuid.UUID,
        question: str,
        limit: int = 3,
    ) -> RAGAnswerResult:
        normalized_question = question.strip()

        if not normalized_question:
            raise RAGAnswerError(
                "Question cannot be empty."
            )

        matches = search_knowledge(
            db,
            organization_id=organization_id,
            query=normalized_question,
            limit=limit,
        )

        if not matches:
            return RAGAnswerResult(
                answer=(
                    "The available approved company knowledge "
                    "does not contain enough information to answer "
                    "this request. Human review is required."
                ),
                sources=[],
                insufficient_knowledge=True,
            )

        context_blocks: list[str] = []
        sources: list[RAGSource] = []

        for index, match in enumerate(
            matches,
            start=1,
        ):
            metadata = match.chunk.metadata_json or {}
            page_value = metadata.get("page")

            page = (
                int(page_value)
                if isinstance(page_value, int)
                else None
            )

            context_blocks.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        (
                            "Document: "
                            f"{match.document.original_filename}"
                        ),
                        f"Page: {page or 'unknown'}",
                        f"Content: {match.chunk.content}",
                    ]
                )
            )

            sources.append(
                RAGSource(
                    document_id=match.document.id,
                    chunk_id=match.chunk.id,
                    filename=(
                        match.document.original_filename
                    ),
                    page=page,
                    score=match.score,
                )
            )

        context = "\n\n".join(context_blocks)

        system_prompt = (
            "You are the AI Sales Agent for a company. "
            "Prepare a professional, reviewable customer-facing "
            "response using only the approved company knowledge "
            "provided in the context. "

            "STRICT GROUNDING RULES: "
            "Every company-specific factual statement must be "
            "supported by the approved company knowledge. "
            "Never invent or infer prices, quotations, discounts, "
            "stock levels, current availability, delivery promises, "
            "payment terms, warranties, policies, product "
            "specifications, or other company facts that are not "
            "explicitly supported by the context. "

            "REQUEST-SCOPE RULE: "
            "Answer only the information the customer actually "
            "asked for. "
            "Do not add unrelated facts merely because they are "
            "present in the approved knowledge. "
            "For example, if the customer asks about pricing, "
            "availability, delivery, and payment terms, do not "
            "volunteer warranty information or quotation validity "
            "unless the customer specifically asked for them. "

            "PARTIAL-KNOWLEDGE RULE: "
            "Evaluate each requested item separately. "
            "If approved knowledge supports some requested items "
            "but not others, answer the supported items and clearly "
            "state that unsupported items require confirmation or "
            "human review. "
            "Do not reject the entire request merely because one "
            "part is unsupported. "

            "For example, if approved knowledge provides payment "
            "terms and standard delivery information but does not "
            "provide current pricing or current availability, "
            "provide the supported payment and delivery information "
            "and state that pricing and current availability require "
            "confirmation. "

            "INSUFFICIENT-KNOWLEDGE RULE: "
            "If none of the customer's requested information is "
            "supported by approved knowledge, clearly state that "
            "the available approved company knowledge does not "
            "contain enough information and human review is required. "

            "NO-COMMITMENT RULE: "
            "Do not promise a response time, callback, quotation "
            "delivery time, stock check, follow-up deadline, or "
            "future action unless such a commitment is explicitly "
            "provided in the approved knowledge. "
            "Do not say phrases such as 'I will get back to you "
            "shortly', 'please allow me some time', or 'we will "
            "respond promptly'. "
            "Instead state that missing information requires "
            "confirmation or human review. "

            "Do not claim that an item is in stock unless the "
            "context explicitly confirms current stock. "
            "Do not generate or estimate a price unless an approved "
            "price is explicitly present in the context. "

            "Keep the response concise and professional. "
            "Do not mention RAG, retrieval, prompts, chunks, source "
            "numbers, databases, internal implementation details, "
            "or that information came from a provided context."
        )

        user_prompt = (
            "Customer request:\n"
            f"{normalized_question}\n\n"
            "Approved company knowledge:\n"
            f"{context}\n\n"
            "Prepare the customer-facing response according to the "
            "grounding, request-scope, partial-knowledge, "
            "insufficient-knowledge, and no-commitment rules."
        )

        try:
            answer = self.ai.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        except AIProviderError as exc:
            raise RAGAnswerError(
                "Unable to generate a grounded AI answer."
            ) from exc

        normalized_answer = answer.lower()

        insufficient_knowledge = (
            "human review" in normalized_answer
            or "require human review" in normalized_answer
            or "requires human review" in normalized_answer
            or "require confirmation" in normalized_answer
            or "requires confirmation" in normalized_answer
            or "need confirmation" in normalized_answer
            or "needs confirmation" in normalized_answer
            or "need to confirm" in normalized_answer
            or "needs to be confirmed" in normalized_answer
            or "not available" in normalized_answer
            or "does not contain enough information"
            in normalized_answer
        )

        return RAGAnswerResult(
            answer=answer.strip(),
            sources=sources,
            insufficient_knowledge=insufficient_knowledge,
        )