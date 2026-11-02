from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge_document import (
    KnowledgeDocumentStatus,
)


class KnowledgeChunkResponse(BaseModel):
    """Stored chunk belonging to a knowledge document."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    organization_id: UUID
    document_id: UUID

    chunk_index: int = Field(
        ge=0,
    )

    content: str = Field(
        min_length=1,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )

    created_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    """Knowledge document metadata."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    organization_id: UUID
    uploaded_by: UUID

    filename: str
    original_filename: str
    mime_type: str

    file_size: int = Field(
        ge=0,
    )

    status: KnowledgeDocumentStatus

    title: str | None = None

    checksum: str = Field(
        min_length=64,
        max_length=64,
    )

    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListResponse(BaseModel):
    """Paginated knowledge-document list."""

    items: list[KnowledgeDocumentResponse]

    total: int = Field(
        ge=0,
    )

    page: int = Field(
        ge=1,
    )

    page_size: int = Field(
        ge=1,
    )


class KnowledgeSearchRequest(BaseModel):
    """Search approved organization knowledge."""

    query: str = Field(
        min_length=2,
        max_length=1000,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )


class KnowledgeSearchResult(BaseModel):
    """One relevant knowledge chunk."""

    chunk_id: UUID
    document_id: UUID

    document_title: str | None = None
    original_filename: str

    chunk_index: int

    content: str

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    score: float = Field(
        ge=0.0,
    )


class KnowledgeSearchResponse(BaseModel):
    """Ranked organization-scoped knowledge results."""

    query: str

    results: list[KnowledgeSearchResult] = Field(
        default_factory=list,
    )


class RAGAnswerRequest(BaseModel):
    """Request a grounded company-knowledge answer."""

    question: str = Field(
        min_length=2,
        max_length=2000,
    )

    limit: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class RAGAnswerSourceResponse(BaseModel):
    """Source supporting a grounded answer."""

    document_id: UUID
    chunk_id: UUID

    filename: str

    page: int | None = None

    score: float = Field(
        ge=0.0,
    )


class RAGAnswerResponse(BaseModel):
    """Grounded RAG answer response."""

    answer: str = Field(
        min_length=1,
    )

    insufficient_knowledge: bool

    sources: list[RAGAnswerSourceResponse] = Field(
        default_factory=list,
    )