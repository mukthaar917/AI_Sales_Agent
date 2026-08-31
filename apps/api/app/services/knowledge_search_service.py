from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import (
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)


_TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)*"
)


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "to",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}


@dataclass(frozen=True)
class KnowledgeSearchMatch:
    """Internal ranked knowledge-search result."""

    chunk: KnowledgeChunk
    document: KnowledgeDocument
    score: float


def _tokenize(text: str) -> list[str]:
    """
    Normalize text into useful search tokens.

    Common question words are removed so terms such as
    payment, warranty and delivery drive retrieval.
    """

    tokens = [
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
    ]

    return [
        token
        for token in tokens
        if (
            len(token) >= 2
            and token not in _STOP_WORDS
        )
    ]


def _score_chunk(
    *,
    query: str,
    content: str,
) -> float:
    """
    Calculate deterministic lexical relevance.

    This is intentionally simple for the first RAG
    retrieval implementation. It can later be replaced
    or supplemented with vector similarity.
    """

    query_tokens = _tokenize(query)

    if not query_tokens:
        return 0.0

    content_lower = content.lower()
    content_tokens = _tokenize(content)

    if not content_tokens:
        return 0.0

    content_token_set = set(content_tokens)

    unique_query_tokens = set(query_tokens)

    matched_tokens = {
        token
        for token in unique_query_tokens
        if token in content_token_set
    }

    if not matched_tokens:
        return 0.0

    token_coverage = (
        len(matched_tokens)
        / len(unique_query_tokens)
    )

    occurrence_bonus = 0.0

    for token in matched_tokens:
        occurrences = content_tokens.count(token)

        occurrence_bonus += min(
            occurrences,
            3,
        ) * 0.05

    phrase_bonus = 0.0

    normalized_query = " ".join(query_tokens)

    if (
        normalized_query
        and normalized_query in content_lower
    ):
        phrase_bonus = 0.5

    score = (
        token_coverage
        + occurrence_bonus
        + phrase_bonus
    )

    return round(score, 6)


def search_knowledge(
    db: Session,
    *,
    organization_id: uuid.UUID,
    query: str,
    limit: int = 5,
) -> list[KnowledgeSearchMatch]:
    """
    Search READY knowledge for one organization.

    Tenant isolation is enforced in the SQL query,
    before any ranking occurs.
    """

    normalized_query = query.strip()

    if not normalized_query:
        return []

    rows = db.execute(
        select(
            KnowledgeChunk,
            KnowledgeDocument,
        )
        .join(
            KnowledgeDocument,
            KnowledgeDocument.id
            == KnowledgeChunk.document_id,
        )
        .where(
            KnowledgeChunk.organization_id
            == organization_id,
            KnowledgeDocument.organization_id
            == organization_id,
            KnowledgeDocument.status
            == KnowledgeDocumentStatus.READY,
        )
    ).all()

    matches: list[KnowledgeSearchMatch] = []

    for chunk, document in rows:
        score = _score_chunk(
            query=normalized_query,
            content=chunk.content,
        )

        if score <= 0:
            continue

        matches.append(
            KnowledgeSearchMatch(
                chunk=chunk,
                document=document,
                score=score,
            )
        )

    matches.sort(
        key=lambda item: (
            -item.score,
            item.document.created_at,
            item.chunk.chunk_index,
        )
    )

    return matches[:limit]