"""Email synchronization and inbox API endpoints."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.encryption import (
    EncryptionConfigurationError,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
)
from app.db.session import get_db
from app.models.email_message import EmailMessage
from app.models.email_thread import EmailThread
from app.models.gmail_connection import GmailConnection
from app.models.user import User
from app.schemas.email import (
    CreateQuotationFromThreadResponse,
    DraftReplyRequest,
    DraftReplyResponse,
    EmailMessageResponse,
    EmailThreadDetail,
    EmailThreadListResponse,
    EmailThreadSummary,
    EmailThreadSummaryResponse,
    QuotationDraftRequest,
    QuotationDraftResponse,
    QuotationExtractionResponse,
    QuotationPreviewResponse,
    ReplySuggestionsResponse,
    SalesOpportunityResponse,
)
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
)
from app.services.email_summary import (
    EmailSummaryError,
    EmailSummaryService,
)
from app.services.gmail.client import (
    GmailClient,
    GmailClientError,
)
from app.services.gmail.drafts import (
    GmailDraftError,
    GmailDraftService,
)
from app.services.gmail.oauth import (
    GmailOAuthError,
    GmailOAuthService,
)
from app.services.gmail.sync import (
    GmailSyncError,
    GmailSyncService,
)
from app.services.quotation_extraction import (
    QuotationExtractionError,
    QuotationExtractionService,
)
from app.services.quotation_pdf_service import (
    generate_quotation_pdf,
)
from app.services.quotation_preview import (
    QuotationPreviewError,
    QuotationPreviewService,
)
from app.services.quotation_service import (
    create_quotation,
    get_customer_for_organization,
    get_quotation_by_id,
)
from app.services.reply_suggestions import (
    ReplySuggestionError,
    ReplySuggestionService,
)
from app.services.sales_opportunity import (
    SalesOpportunityError,
    SalesOpportunityService,
)


router = APIRouter()


class GmailSyncResponse(BaseModel):
    """Gmail synchronization statistics."""

    fetched: int
    created: int
    updated: int
    skipped: int
    failed: int


def _deserialize_scopes(
    scopes_value: str | None,
) -> list[str]:
    """Deserialize stored OAuth scopes safely."""

    if not scopes_value:
        return []

    try:
        parsed_scopes = json.loads(scopes_value)

        if isinstance(parsed_scopes, list):
            return [
                str(scope).strip()
                for scope in parsed_scopes
                if str(scope).strip()
            ]
    except (json.JSONDecodeError, TypeError):
        pass

    return [
        scope.strip()
        for scope in scopes_value.replace(",", " ").split()
        if scope.strip()
    ]


def _get_active_gmail_connection(
    db: Session,
    current_user: User,
) -> GmailConnection | None:
    """Return the active Gmail connection for one user and tenant."""

    statement = select(GmailConnection).where(
        GmailConnection.organization_id
        == current_user.organization_id,
        GmailConnection.user_id
        == current_user.id,
        GmailConnection.is_active.is_(True),
    )

    return db.scalar(statement)


def _thread_message_order():
    """Return chronological ordering for thread messages."""

    return (
        case(
            (
                EmailMessage.received_at.is_not(None),
                EmailMessage.received_at,
            ),
            else_=EmailMessage.sent_at,
        ).asc().nullslast(),
        EmailMessage.created_at.asc(),
    )


def _latest_message_order():
    """Return reverse chronological ordering for thread messages."""

    return (
        case(
            (
                EmailMessage.received_at.is_not(None),
                EmailMessage.received_at,
            ),
            else_=EmailMessage.sent_at,
        ).desc().nullslast(),
        EmailMessage.created_at.desc(),
    )


def _get_valid_gmail_access_token(
    db: Session,
    connection: GmailConnection,
) -> str:
    """Return a valid Gmail access token, refreshing when necessary."""

    access_token = decrypt_secret(
        connection.access_token_encrypted
    )

    token_expired = (
        connection.token_expiry is not None
        and connection.token_expiry
        <= datetime.now(timezone.utc)
    )

    if not token_expired:
        return access_token

    if not connection.refresh_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Gmail must be reconnected before "
                "this operation can continue."
            ),
        )

    refresh_token = decrypt_secret(
        connection.refresh_token_encrypted
    )

    refreshed_credentials = (
        GmailOAuthService()
        .refresh_access_token(refresh_token)
    )

    refreshed_access_token = str(
        refreshed_credentials.get(
            "access_token",
            "",
        )
    ).strip()

    if not refreshed_access_token:
        raise GmailOAuthError(
            "Google did not return an access token."
        )

    connection.access_token_encrypted = encrypt_secret(
        refreshed_access_token
    )

    connection.token_expiry = (
        refreshed_credentials.get("token_expiry")
    )

    refreshed_refresh_token = str(
        refreshed_credentials.get(
            "refresh_token",
            "",
        )
        or ""
    ).strip()

    if refreshed_refresh_token:
        connection.refresh_token_encrypted = encrypt_secret(
            refreshed_refresh_token
        )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    return refreshed_access_token


@router.post(
    "/sync",
    response_model=GmailSyncResponse,
    status_code=status.HTTP_200_OK,
)
def sync_gmail_inbox(
    max_results: int = Query(
        default=25,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GmailSyncResponse:
    """Synchronize Gmail inbox messages for the authenticated user."""

    connection = _get_active_gmail_connection(
        db=db,
        current_user=current_user,
    )

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Gmail connection was found.",
        )

    try:
        access_token = _get_valid_gmail_access_token(
            db=db,
            connection=connection,
        )

        gmail_client = GmailClient(
            access_token=access_token,
            scopes=_deserialize_scopes(
                connection.scopes
            ),
        )

        sync_service = GmailSyncService(
            db=db,
            gmail_client=gmail_client,
            connection=connection,
        )

        statistics = sync_service.sync_inbox(
            max_results=max_results
        )

        return GmailSyncResponse(**statistics)

    except HTTPException:
        raise

    except (
        EncryptionConfigurationError,
        SecretDecryptionError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored Gmail credentials are unavailable.",
        ) from None

    except GmailOAuthError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to refresh the Gmail connection.",
        ) from None

    except (
        GmailClientError,
        GmailSyncError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to synchronize the Gmail inbox.",
        ) from None

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save Gmail synchronization results.",
        ) from None


@router.get(
    "/threads",
    response_model=EmailThreadListResponse,
    status_code=status.HTTP_200_OK,
)
def list_email_threads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    sender: str | None = Query(
        default=None,
        min_length=1,
        max_length=320,
    ),
    unread: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadListResponse:
    """Return synchronized email threads for the current organization."""

    thread_filters = [
        EmailThread.organization_id
        == current_user.organization_id,
    ]

    if unread is not None:
        thread_filters.append(
            EmailThread.unread.is_(unread)
        )

    normalized_search = (
        search.strip()
        if search
        else None
    )

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        sender_thread_ids = (
            select(EmailMessage.thread_id)
            .where(
                EmailMessage.organization_id
                == current_user.organization_id,
                EmailMessage.sender_email.ilike(
                    search_pattern
                ),
            )
        )

        thread_filters.append(
            or_(
                EmailThread.subject.ilike(
                    search_pattern
                ),
                EmailThread.snippet.ilike(
                    search_pattern
                ),
                EmailThread.id.in_(
                    sender_thread_ids
                ),
            )
        )

    normalized_sender = (
        sender.strip()
        if sender
        else None
    )

    if normalized_sender:
        sender_pattern = f"%{normalized_sender}%"

        sender_thread_ids = (
            select(EmailMessage.thread_id)
            .where(
                EmailMessage.organization_id
                == current_user.organization_id,
                EmailMessage.sender_email.ilike(
                    sender_pattern
                ),
            )
        )

        thread_filters.append(
            EmailThread.id.in_(
                sender_thread_ids
            )
        )

    total_statement = (
        select(func.count())
        .select_from(EmailThread)
        .where(*thread_filters)
    )

    total = db.scalar(total_statement) or 0

    message_count_subquery = (
        select(
            EmailMessage.thread_id.label(
                "thread_id"
            ),
            func.count(
                EmailMessage.id
            ).label(
                "message_count"
            ),
        )
        .where(
            EmailMessage.organization_id
            == current_user.organization_id
        )
        .group_by(
            EmailMessage.thread_id
        )
        .subquery()
    )

    thread_statement = (
        select(
            EmailThread,
            func.coalesce(
                message_count_subquery.c.message_count,
                0,
            ).label("message_count"),
        )
        .outerjoin(
            message_count_subquery,
            message_count_subquery.c.thread_id
            == EmailThread.id,
        )
        .where(*thread_filters)
        .order_by(
            EmailThread.last_message_at
            .desc()
            .nullslast(),
            EmailThread.created_at.desc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    rows = db.execute(
        thread_statement
    ).all()

    items = [
        EmailThreadSummary(
            id=thread.id,
            provider_thread_id=thread.provider_thread_id,
            subject=thread.subject,
            snippet=thread.snippet,
            participant_emails=(
                thread.participant_emails or []
            ),
            last_message_at=thread.last_message_at,
            unread=thread.unread,
            message_count=int(message_count),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )
        for thread, message_count in rows
    ]

    total_pages = (
        math.ceil(total / page_size)
        if total
        else 0
    )

    return EmailThreadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/threads/{thread_id}",
    response_model=EmailThreadDetail,
    status_code=status.HTTP_200_OK,
)
def get_email_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadDetail:
    """Return one email thread and its messages."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    return EmailThreadDetail(
        id=thread.id,
        provider_thread_id=thread.provider_thread_id,
        subject=thread.subject,
        snippet=thread.snippet,
        participant_emails=(
            thread.participant_emails or []
        ),
        last_message_at=thread.last_message_at,
        unread=thread.unread,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        messages=[
            EmailMessageResponse.model_validate(
                message
            )
            for message in messages
        ],
    )


@router.post(
    "/threads/{thread_id}/summary",
    response_model=EmailThreadSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def summarize_email_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailThreadSummaryResponse:
    """Generate a concise summary for one synchronized email thread."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    try:
        summary = EmailSummaryService().summarize(
            thread=thread,
            messages=list(messages),
        )
    except EmailSummaryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return EmailThreadSummaryResponse(
        thread_id=thread.id,
        summary=summary,
        message_count=len(messages),
    )


@router.post(
    "/threads/{thread_id}/reply-suggestions",
    response_model=ReplySuggestionsResponse,
    status_code=status.HTTP_200_OK,
)
def generate_reply_suggestions(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReplySuggestionsResponse:
    """Generate reviewable reply suggestions for one email thread."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    try:
        suggestions = ReplySuggestionService().generate(
            thread=thread,
            messages=list(messages),
        )
    except ReplySuggestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ReplySuggestionsResponse(
        thread_id=thread.id,
        suggestions=suggestions,
    )


@router.post(
    "/threads/{thread_id}/sales-opportunity",
    response_model=SalesOpportunityResponse,
    status_code=status.HTTP_200_OK,
)
def detect_sales_opportunity(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesOpportunityResponse:
    """Classify whether an email thread is a sales opportunity."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    try:
        result = SalesOpportunityService().detect(
            thread=thread,
            messages=list(messages),
        )
    except SalesOpportunityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return SalesOpportunityResponse(
        thread_id=thread.id,
        classification=result.classification,
        confidence=result.confidence,
        reason=result.reason,
    )


@router.post(
    "/threads/{thread_id}/quotation-extraction",
    response_model=QuotationExtractionResponse,
    status_code=status.HTTP_200_OK,
)
def extract_quotation_requirements(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationExtractionResponse:
    """Extract quotation requirements from an email thread."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    try:
        result = QuotationExtractionService().extract(
            thread=thread,
            messages=list(messages),
        )
    except QuotationExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return QuotationExtractionResponse(
        thread_id=thread.id,
        product=result.product,
        quantity=result.quantity,
        pricing_requested=result.pricing_requested,
        availability_requested=result.availability_requested,
        delivery_requested=result.delivery_requested,
        payment_terms_requested=(
            result.payment_terms_requested
        ),
        confidence=result.confidence,
    )


@router.post(
    "/threads/{thread_id}/quotation-preview",
    response_model=QuotationPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_quotation_from_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationPreviewResponse:
    """Prepare a reviewable quotation preview from an RFQ email."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email thread does not contain any messages.",
        )

    incoming_messages = [
        message
        for message in messages
        if (
            message.direction == "incoming"
            and message.sender_email
        )
    ]

    if not incoming_messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine the RFQ sender.",
        )

    sender_email = incoming_messages[-1].sender_email

    if sender_email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine the RFQ sender email.",
        )

    try:
        extraction = QuotationExtractionService().extract(
            thread=thread,
            messages=list(messages),
        )

        if (
            extraction.product is None
            or extraction.quantity is None
        ):
            raise QuotationPreviewError(
                "Product or quantity could not be extracted."
            )

        preview = QuotationPreviewService(
            db=db,
        ).prepare(
            current_user=current_user,
            sender_email=sender_email,
            product_name=extraction.product,
            quantity=extraction.quantity,
        )

    except (
        QuotationExtractionError,
        QuotationPreviewError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return QuotationPreviewResponse(
        thread_id=thread.id,
        customer_id=preview.customer_id,
        customer_name=preview.customer_name,
        customer_email=preview.customer_email,
        product_id=preview.product_id,
        product_name=preview.product_name,
        quantity=preview.quantity,
        unit=preview.unit,
        unit_price=preview.unit_price,
        currency=preview.currency,
        tax_rate=preview.tax_rate,
        subtotal=preview.subtotal,
        tax_amount=preview.tax_amount,
        total_amount=preview.total_amount,
    )


@router.post(
    "/threads/{thread_id}/quotation",
    response_model=CreateQuotationFromThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation_from_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateQuotationFromThreadResponse:
    """Create a draft quotation from a reviewed RFQ email thread."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
        .order_by(
            *_thread_message_order(),
        )
    ).all()

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email thread does not contain any messages.",
        )

    incoming_messages = [
        message
        for message in messages
        if (
            message.direction == "incoming"
            and message.sender_email
        )
    ]

    if not incoming_messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine the RFQ sender.",
        )

    sender_email = incoming_messages[-1].sender_email

    if sender_email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine the RFQ sender email.",
        )

    try:
        extraction = QuotationExtractionService().extract(
            thread=thread,
            messages=list(messages),
        )

        if (
            extraction.product is None
            or extraction.quantity is None
        ):
            raise QuotationPreviewError(
                "Product or quantity could not be extracted."
            )

        preview = QuotationPreviewService(
            db=db,
        ).prepare(
            current_user=current_user,
            sender_email=sender_email,
            product_name=extraction.product,
            quantity=extraction.quantity,
        )

        today = date.today()

        quotation_in = QuotationCreate(
            customer_id=UUID(preview.customer_id),
            issue_date=today,
            expiry_date=today + timedelta(days=14),
            currency=preview.currency,
            notes=(
                f"Created from email thread {thread.id}. "
                f"Original subject: "
                f"{thread.subject or 'No subject'}"
            ),
            terms=(
                "Draft quotation created from reviewed "
                "RFQ requirements."
            ),
            items=[
                QuotationItemCreate(
                    product_id=UUID(preview.product_id),
                    description=preview.product_name,
                    quantity=preview.quantity,
                    unit=preview.unit,
                    unit_price=preview.unit_price,
                    discount_rate=Decimal("0.00"),
                    tax_rate=preview.tax_rate,
                    sort_order=1,
                )
            ],
        )

        quotation = create_quotation(
            db=db,
            quotation_in=quotation_in,
            current_user=current_user,
        )

    except (
        QuotationExtractionError,
        QuotationPreviewError,
        ValueError,
    ) as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the quotation.",
        ) from None

    return CreateQuotationFromThreadResponse(
        thread_id=thread.id,
        quotation_id=quotation.id,
        quotation_number=quotation.quotation_number,
        status=quotation.status.value,
    )


@router.post(
    "/threads/{thread_id}/quotation-draft",
    response_model=QuotationDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation_draft(
    thread_id: UUID,
    payload: QuotationDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDraftResponse:
    """
    Create a Gmail draft reply with a quotation PDF attached.

    This creates a draft only and does not send the email.
    """

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    latest_message = db.scalar(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
            EmailMessage.direction == "incoming",
        )
        .order_by(
            *_latest_message_order(),
        )
        .limit(1)
    )

    if latest_message is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The email thread does not contain "
                "an incoming message to reply to."
            ),
        )

    recipient = (
        latest_message.sender_email.strip()
        if latest_message.sender_email
        else ""
    )

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A quotation recipient could not be "
                "determined for this thread."
            ),
        )

    quotation = get_quotation_by_id(
        db=db,
        quotation_id=payload.quotation_id,
        organization_id=current_user.organization_id,
    )

    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation was not found.",
        )

    customer = get_customer_for_organization(
        db=db,
        customer_id=quotation.customer_id,
        organization_id=current_user.organization_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Quotation customer was not found "
                "or is inactive."
            ),
        )

    customer_email = (
        customer.email.strip().lower()
        if customer.email
        else ""
    )

    if (
        customer_email
        and customer_email != recipient.lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The quotation customer email does not "
                "match the RFQ sender."
            ),
        )

    try:
        pdf_bytes = generate_quotation_pdf(
            quotation=quotation,
            customer=customer,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate the quotation PDF.",
        ) from exc

    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated quotation PDF is empty.",
        )

    attachment_filename = (
        f"{quotation.quotation_number}.pdf"
    )

    contact_name = (
        customer.contact_name.strip()
        if customer.contact_name
        else ""
    )

    greeting = (
        f"Dear {contact_name},"
        if contact_name
        else "Hello,"
    )

    subject = (
        thread.subject
        or f"Quotation {quotation.quotation_number}"
    )

    body = "\n".join(
        [
            greeting,
            "",
            "Thank you for your enquiry.",
            "",
            (
                "Please find attached our quotation "
                f"{quotation.quotation_number} for your review."
            ),
            "",
            (
                "The quotation is valid until "
                f"{quotation.expiry_date.isoformat()}."
            ),
            "",
            (
                "Please review the attached document and "
                "let us know if you have any questions "
                "or require any changes."
            ),
            "",
            "Best regards,",
            "Sales Team",
        ]
    )

    connection = _get_active_gmail_connection(
        db=db,
        current_user=current_user,
    )

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Gmail connection was found.",
        )

    try:
        access_token = _get_valid_gmail_access_token(
            db=db,
            connection=connection,
        )

        gmail_client = GmailClient(
            access_token=access_token,
            scopes=_deserialize_scopes(
                connection.scopes
            ),
        )

        result = GmailDraftService(
            gmail_client=gmail_client,
        ).create_thread_reply_draft(
            thread=thread,
            latest_message=latest_message,
            subject=subject,
            body=body,
            attachments=[
                (
                    attachment_filename,
                    pdf_bytes,
                    "application/pdf",
                )
            ],
        )

    except HTTPException:
        raise

    except (
        EncryptionConfigurationError,
        SecretDecryptionError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored Gmail credentials are unavailable.",
        ) from None

    except GmailOAuthError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to refresh the Gmail connection.",
        ) from None

    except (
        GmailDraftError,
        GmailClientError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return QuotationDraftResponse(
        thread_id=thread.id,
        quotation_id=quotation.id,
        quotation_number=quotation.quotation_number,
        draft_id=result.draft_id,
        message_id=result.message_id,
        recipient=recipient,
        attachment_filename=attachment_filename,
        status="draft",
    )


@router.post(
    "/threads/{thread_id}/draft-reply",
    response_model=DraftReplyResponse,
    status_code=status.HTTP_200_OK,
)
def create_thread_draft_reply(
    thread_id: UUID,
    payload: DraftReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReplyResponse:
    """Create a Gmail draft reply without sending the email."""

    thread = db.scalar(
        select(EmailThread).where(
            EmailThread.id == thread_id,
            EmailThread.organization_id
            == current_user.organization_id,
        )
    )

    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email thread was not found.",
        )

    latest_message = db.scalar(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == thread.id,
            EmailMessage.organization_id
            == current_user.organization_id,
            EmailMessage.direction == "incoming",
        )
        .order_by(
            *_latest_message_order(),
        )
        .limit(1)
    )

    if latest_message is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The email thread does not contain "
                "an incoming message to reply to."
            ),
        )

    if not latest_message.sender_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A reply recipient could not be "
                "determined for this thread."
            ),
        )

    connection = _get_active_gmail_connection(
        db=db,
        current_user=current_user,
    )

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Gmail connection was found.",
        )

    try:
        access_token = _get_valid_gmail_access_token(
            db=db,
            connection=connection,
        )

        gmail_client = GmailClient(
            access_token=access_token,
            scopes=_deserialize_scopes(
                connection.scopes
            ),
        )

        result = GmailDraftService(
            gmail_client=gmail_client,
        ).create_thread_reply_draft(
            thread=thread,
            latest_message=latest_message,
            subject=payload.subject,
            body=payload.body,
        )

    except HTTPException:
        raise

    except (
        EncryptionConfigurationError,
        SecretDecryptionError,
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored Gmail credentials are unavailable.",
        ) from None

    except GmailOAuthError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to refresh the Gmail connection.",
        ) from None

    except (
        GmailDraftError,
        GmailClientError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return DraftReplyResponse(
        thread_id=thread.id,
        draft_id=result.draft_id,
        message_id=result.message_id,
        status="draft",
    )


@router.get(
    "/messages/{message_id}",
    response_model=EmailMessageResponse,
    status_code=status.HTTP_200_OK,
)
def get_email_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailMessageResponse:
    """Return one synchronized email message."""

    message = db.scalar(
        select(EmailMessage).where(
            EmailMessage.id == message_id,
            EmailMessage.organization_id
            == current_user.organization_id,
        )
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email message was not found.",
        )

    return EmailMessageResponse.model_validate(
        message
    )