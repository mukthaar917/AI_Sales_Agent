from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import (
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)


class KnowledgeDocumentError(RuntimeError):
    """Raised when a knowledge document cannot be processed."""


@dataclass
class ExtractedPage:
    """Extracted text associated with one source page."""

    page_number: int | None
    text: str


@dataclass
class KnowledgeTextChunk:
    """One normalized chunk ready for database storage."""

    chunk_index: int
    content: str
    metadata: dict[str, object]


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
}


def normalize_text(value: str) -> str:
    """Normalize extracted text without changing its meaning."""

    value = value.replace("\x00", "")
    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    lines: list[str] = []

    for raw_line in value.split("\n"):
        line = re.sub(
            r"[ \t]+",
            " ",
            raw_line,
        ).strip()

        lines.append(line)

    normalized_lines: list[str] = []
    previous_blank = False

    for line in lines:
        if not line:
            if not previous_blank:
                normalized_lines.append("")

            previous_blank = True
            continue

        normalized_lines.append(line)
        previous_blank = False

    return "\n".join(
        normalized_lines
    ).strip()


def _guess_mime_type(
    path: Path,
) -> str:
    """Return the MIME type for a supported document."""

    suffix = path.suffix.lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }

    mime_type = mime_types.get(suffix)

    if mime_type is None:
        raise KnowledgeDocumentError(
            f"Unsupported document type: "
            f"{suffix or 'unknown'}"
        )

    return mime_type


def extract_pdf(
    path: Path,
) -> list[ExtractedPage]:
    """Extract text from a PDF without OCR."""

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise KnowledgeDocumentError(
            "Unable to read the PDF document."
        ) from exc

    pages: list[ExtractedPage] = []

    for page_index, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise KnowledgeDocumentError(
                f"Unable to extract PDF page "
                f"{page_index}."
            ) from exc

        normalized = normalize_text(text)

        if normalized:
            pages.append(
                ExtractedPage(
                    page_number=page_index,
                    text=normalized,
                )
            )

    if not pages:
        raise KnowledgeDocumentError(
            "The PDF does not contain extractable text."
        )

    return pages


def extract_text_file(
    path: Path,
) -> list[ExtractedPage]:
    """Extract UTF-8 text from TXT or Markdown."""

    try:
        content = path.read_text(
            encoding="utf-8",
        )
    except UnicodeDecodeError as exc:
        raise KnowledgeDocumentError(
            "Text document must use UTF-8 encoding."
        ) from exc
    except OSError as exc:
        raise KnowledgeDocumentError(
            "Unable to read the text document."
        ) from exc

    normalized = normalize_text(content)

    if not normalized:
        raise KnowledgeDocumentError(
            "The document does not contain meaningful text."
        )

    return [
        ExtractedPage(
            page_number=None,
            text=normalized,
        )
    ]


def extract_document(
    file_path: str | Path,
) -> list[ExtractedPage]:
    """Extract normalized text from a supported document."""

    path = Path(file_path)

    if not path.exists():
        raise KnowledgeDocumentError(
            "Knowledge document was not found."
        )

    if not path.is_file():
        raise KnowledgeDocumentError(
            "Knowledge document path is not a file."
        )

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise KnowledgeDocumentError(
            f"Unsupported document type: "
            f"{suffix or 'unknown'}"
        )

    if suffix == ".pdf":
        return extract_pdf(path)

    return extract_text_file(path)


def _split_text(
    text: str,
    *,
    target_size: int,
    overlap: int,
) -> list[str]:
    """Split text into deterministic overlapping chunks."""

    if target_size < 200:
        raise ValueError(
            "target_size must be at least 200 characters."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= target_size:
        raise ValueError(
            "overlap must be smaller than target_size."
        )

    text = text.strip()

    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        tentative_end = min(
            start + target_size,
            text_length,
        )

        end = tentative_end

        if tentative_end < text_length:
            paragraph_break = text.rfind(
                "\n\n",
                start,
                tentative_end,
            )

            sentence_break = max(
                text.rfind(
                    ". ",
                    start,
                    tentative_end,
                ),
                text.rfind(
                    "? ",
                    start,
                    tentative_end,
                ),
                text.rfind(
                    "! ",
                    start,
                    tentative_end,
                ),
            )

            whitespace_break = text.rfind(
                " ",
                start,
                tentative_end,
            )

            candidate_breaks = [
                position
                for position in (
                    paragraph_break,
                    sentence_break,
                    whitespace_break,
                )
                if position > start
            ]

            if candidate_breaks:
                best_break = max(
                    candidate_breaks
                )

                minimum_useful_end = (
                    start + target_size // 2
                )

                if best_break >= minimum_useful_end:
                    end = best_break

                    if text[end:end + 2] in {
                        ". ",
                        "? ",
                        "! ",
                    }:
                        end += 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(
            end - overlap,
            start + 1,
        )

        while (
            next_start < end
            and next_start > 0
            and not text[
                next_start - 1
            ].isspace()
        ):
            next_start += 1

        start = min(
            next_start,
            text_length,
        )

    return chunks


def build_chunks(
    pages: list[ExtractedPage],
    *,
    source_filename: str,
    target_size: int = 800,
    overlap: int = 120,
) -> list[KnowledgeTextChunk]:
    """Create database-ready chunks from extracted pages."""

    chunks: list[KnowledgeTextChunk] = []
    chunk_index = 0

    for page in pages:
        page_chunks = _split_text(
            page.text,
            target_size=target_size,
            overlap=overlap,
        )

        for content in page_chunks:
            metadata: dict[str, object] = {
                "source_filename": source_filename,
            }

            if page.page_number is not None:
                metadata["page"] = (
                    page.page_number
                )

            chunks.append(
                KnowledgeTextChunk(
                    chunk_index=chunk_index,
                    content=content,
                    metadata=metadata,
                )
            )

            chunk_index += 1

    if not chunks:
        raise KnowledgeDocumentError(
            "The document did not produce "
            "any usable chunks."
        )

    return chunks


def process_document(
    file_path: str | Path,
    *,
    target_size: int = 800,
    overlap: int = 120,
) -> tuple[
    list[ExtractedPage],
    list[KnowledgeTextChunk],
]:
    """
    Extract, normalize, and chunk one supported document.
    """

    path = Path(file_path)

    pages = extract_document(path)

    chunks = build_chunks(
        pages,
        source_filename=path.name,
        target_size=target_size,
        overlap=overlap,
    )

    return pages, chunks


def persist_processed_document(
    db: Session,
    *,
    organization_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    file_path: str | Path,
    title: str | None = None,
    target_size: int = 800,
    overlap: int = 120,
) -> KnowledgeDocument:
    """
    Process and persist a knowledge document.

    Successful flow:
        uploaded -> processing -> ready

    Processing failures are recorded with status=failed
    when possible.
    """

    path = Path(file_path)

    if not path.exists():
        raise KnowledgeDocumentError(
            "Knowledge document was not found."
        )

    if not path.is_file():
        raise KnowledgeDocumentError(
            "Knowledge document path is not a file."
        )

    # Validate the extension before touching the database.
    mime_type = _guess_mime_type(path)

    try:
        file_bytes = path.read_bytes()
    except OSError as exc:
        raise KnowledgeDocumentError(
            "Unable to read the knowledge document."
        ) from exc

    if not file_bytes:
        raise KnowledgeDocumentError(
            "Knowledge document is empty."
        )

    checksum = hashlib.sha256(
        file_bytes
    ).hexdigest()

    existing = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.organization_id
            == organization_id,
            KnowledgeDocument.checksum
            == checksum,
        )
    )

    if existing is not None:
        raise KnowledgeDocumentError(
            "This document has already been uploaded."
        )

    document = KnowledgeDocument(
        organization_id=organization_id,
        uploaded_by=uploaded_by,
        filename=path.name,
        original_filename=path.name,
        mime_type=mime_type,
        file_size=len(file_bytes),
        status=KnowledgeDocumentStatus.UPLOADED,
        title=title,
        checksum=checksum,
    )

    db.add(document)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()

        raise KnowledgeDocumentError(
            "Unable to create knowledge document."
        ) from exc

    document.status = (
        KnowledgeDocumentStatus.PROCESSING
    )

    try:
        db.flush()

        _, chunks = process_document(
            path,
            target_size=target_size,
            overlap=overlap,
        )

        for chunk in chunks:
            db.add(
                KnowledgeChunk(
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    metadata_json=chunk.metadata,
                )
            )

        document.status = (
            KnowledgeDocumentStatus.READY
        )

        db.commit()
        db.refresh(document)

        return document

    except Exception as exc:
        db.rollback()

        # The first transaction was rolled back, so create a
        # standalone FAILED record to preserve the failure state.
        failed_document = KnowledgeDocument(
            organization_id=organization_id,
            uploaded_by=uploaded_by,
            filename=path.name,
            original_filename=path.name,
            mime_type=mime_type,
            file_size=len(file_bytes),
            status=KnowledgeDocumentStatus.FAILED,
            title=title,
            checksum=checksum,
        )

        db.add(failed_document)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()

        if isinstance(
            exc,
            KnowledgeDocumentError,
        ):
            raise

        raise KnowledgeDocumentError(
            "Unable to process knowledge document."
        ) from exc