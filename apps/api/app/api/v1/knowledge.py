from __future__ import annotations


import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User

from app.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)

from app.services.knowledge_document_service import (
    KnowledgeDocumentError,
    persist_processed_document,
)

from app.services.knowledge_search_service import (
    search_knowledge,
)

from app.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    RAGAnswerRequest,
    RAGAnswerResponse,
    RAGAnswerSourceResponse,
)

from app.services.rag_answer_service import (
    RAGAnswerError,
    RAGAnswerService,
)

router = APIRouter()


SUPPORTED_FILE_TYPES: dict[str, set[str]] = {
    ".pdf": {
        "application/pdf",
    },
    ".txt": {
        "text/plain",
    },
    ".md": {
        "text/markdown",
        "text/plain",
        "application/octet-stream",
    },
}


def _safe_original_filename(
    filename: str | None,
) -> str:
    """
    Return only the final filename component.

    Prevents path traversal such as:
    ../../secret.txt
    """

    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    normalized = filename.replace("\\", "/")
    safe_name = Path(normalized).name.strip()

    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    if len(safe_name) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded filename is too long.",
        )

    return safe_name


def _validate_upload_type(
    *,
    filename: str,
    content_type: str | None,
) -> str:
    """Validate extension and declared MIME type."""

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported document type. "
                "Only PDF, TXT and Markdown are allowed."
            ),
        )

    normalized_content_type = (
        content_type or "application/octet-stream"
    ).split(";", 1)[0].strip().lower()

    allowed_content_types = SUPPORTED_FILE_TYPES[
        extension
    ]

    if normalized_content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "The uploaded file MIME type does not "
                "match the supported document type."
            ),
        )

    return extension


def _build_storage_path(
    *,
    organization_id: uuid.UUID,
    extension: str,
) -> Path:
    """
    Generate an organization-scoped internal storage path.

    The user's filename is never used as the stored
    filesystem filename.
    """

    root = Path(
        settings.knowledge_storage_dir
    ).resolve()

    organization_directory = (
        root / str(organization_id)
    )

    organization_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    internal_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    destination = (
        organization_directory
        / internal_filename
    ).resolve()

    try:
        destination.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document storage path.",
        ) from None

    return destination


def _write_upload(
    *,
    upload: UploadFile,
    destination: Path,
) -> int:
    """
    Copy an uploaded file to disk with a hard size limit.

    Returns the number of bytes written.
    """

    total_size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = upload.file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if (
                    total_size
                    > settings.knowledge_max_upload_bytes
                ):
                    raise HTTPException(
                        status_code=(
                            status.HTTP_413_CONTENT_TOO_LARGE
                        ),
                        detail=(
                            "Knowledge document exceeds "
                            "the maximum upload size."
                        ),
                    )

                output.write(chunk)

    except HTTPException:
        destination.unlink(
            missing_ok=True,
        )
        raise

    except OSError:
        destination.unlink(
            missing_ok=True,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Unable to store uploaded document.",
        ) from None

    if total_size == 0:
        destination.unlink(
            missing_ok=True,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Knowledge document cannot be empty.",
        )

    return total_size


def _get_document_for_organization(
    *,
    db: Session,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    load_chunks: bool = False,
) -> KnowledgeDocument:
    """
    Load a knowledge document belonging to one organization.

    Returning 404 instead of 403 prevents leaking the
    existence of another organization's document.
    """

    statement = select(
        KnowledgeDocument
    ).where(
        KnowledgeDocument.id == document_id,
        KnowledgeDocument.organization_id
        == organization_id,
    )

    if load_chunks:
        statement = statement.options(
            selectinload(
                KnowledgeDocument.chunks
            )
        )

    document = db.scalar(statement)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found.",
        )

    return document


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_knowledge_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDocumentResponse:
    """
    Upload, extract, chunk and persist a company
    knowledge document.

    Supported formats:
    - PDF
    - TXT
    - Markdown
    """

    original_filename = _safe_original_filename(
        file.filename
    )

    extension = _validate_upload_type(
        filename=original_filename,
        content_type=file.content_type,
    )

    normalized_title = (
        title.strip()
        if title
        else None
    )

    if normalized_title == "":
        normalized_title = None

    if (
        normalized_title is not None
        and len(normalized_title) > 255
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Knowledge document title must "
                "not exceed 255 characters."
            ),
        )

    destination = _build_storage_path(
        organization_id=(
            current_user.organization_id
        ),
        extension=extension,
    )

    try:
        _write_upload(
            upload=file,
            destination=destination,
        )

        document = persist_processed_document(
            db,
            organization_id=(
                current_user.organization_id
            ),
            uploaded_by=current_user.id,
            file_path=destination,
            title=normalized_title,
        )

    except KnowledgeDocumentError as exc:
        destination.unlink(
            missing_ok=True,
        )

        message = str(exc)

        if (
            message
            == "This document has already been uploaded."
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=422,
            detail=message,
        ) from exc

    finally:
        file.file.close()

    return KnowledgeDocumentResponse.model_validate(
        document
    )


@router.get(
    "/documents",
    response_model=KnowledgeDocumentListResponse,
)
def list_knowledge_documents(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDocumentListResponse:
    """
    Return knowledge documents for the current
    organization only.
    """

    organization_id = (
        current_user.organization_id
    )

    total = db.scalar(
        select(
            func.count(
                KnowledgeDocument.id
            )
        ).where(
            KnowledgeDocument.organization_id
            == organization_id
        )
    )

    total = int(total or 0)

    offset = (
        page - 1
    ) * page_size

    documents = db.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id
            == organization_id
        )
        .order_by(
            KnowledgeDocument.created_at.desc()
        )
        .offset(offset)
        .limit(page_size)
    ).all()

    return KnowledgeDocumentListResponse(
        items=[
            KnowledgeDocumentResponse.model_validate(
                document
            )
            for document in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
)
def search_organization_knowledge(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeSearchResponse:
    """
    Search READY knowledge belonging to the
    authenticated user's organization.
    """

    normalized_query = payload.query.strip()

    matches = search_knowledge(
        db,
        organization_id=(
            current_user.organization_id
        ),
        query=normalized_query,
        limit=payload.limit,
    )

    results = [
        KnowledgeSearchResult(
            chunk_id=match.chunk.id,
            document_id=match.document.id,
            document_title=match.document.title,
            original_filename=(
                match.document.original_filename
            ),
            chunk_index=(
                match.chunk.chunk_index
            ),
            content=match.chunk.content,
            metadata=dict(
                match.chunk.metadata_json or {}
            ),
            score=match.score,
        )
        for match in matches
    ]

    return KnowledgeSearchResponse(
        query=normalized_query,
        results=results,
    )

@router.post(
    "/answer",
    response_model=RAGAnswerResponse,
)
def answer_from_knowledge(
    payload: RAGAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RAGAnswerResponse:
    """Generate a grounded answer from approved company knowledge."""

    try:
        result = RAGAnswerService().answer(
            db,
            organization_id=current_user.organization_id,
            question=payload.question,
            limit=payload.limit,
        )

    except RAGAnswerError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return RAGAnswerResponse(
        answer=result.answer,
        insufficient_knowledge=result.insufficient_knowledge,
        sources=[
            RAGAnswerSourceResponse(
                document_id=source.document_id,
                chunk_id=source.chunk_id,
                filename=source.filename,
                page=source.page,
                score=source.score,
            )
            for source in result.sources
        ],
    )

@router.get(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
)
def get_knowledge_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDocumentResponse:
    """
    Return one knowledge document belonging to the
    current organization.
    """

    document = _get_document_for_organization(
        db=db,
        organization_id=(
            current_user.organization_id
        ),
        document_id=document_id,
    )

    return KnowledgeDocumentResponse.model_validate(
        document
    )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[KnowledgeChunkResponse],
)
def list_knowledge_document_chunks(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeChunkResponse]:
    """
    Return chunks for one knowledge document.

    The parent document must belong to the current
    organization.
    """

    document = _get_document_for_organization(
        db=db,
        organization_id=(
            current_user.organization_id
        ),
        document_id=document_id,
        load_chunks=True,
    )

    return [
        KnowledgeChunkResponse.model_validate(
            chunk
        )
        for chunk in document.chunks
    ]


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete one knowledge document and its chunks.

    Database chunks are removed through the configured
    cascade relationship / foreign-key cascade.
    """

    document = _get_document_for_organization(
        db=db,
        organization_id=(
            current_user.organization_id
        ),
        document_id=document_id,
    )

    db.delete(document)
    db.commit()

    return None