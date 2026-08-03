
"""Email inbox API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailMessageResponse(BaseModel):
    """A synchronized email message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    thread_id: UUID

    provider_message_id: str
    provider_thread_id: str

    internet_message_id: str | None = None
    in_reply_to: str | None = None
    references_header: str | None = None

    sender_name: str | None = None
    sender_email: str | None = None

    recipient_emails: list[str] = Field(default_factory=list)
    cc_emails: list[str] = Field(default_factory=list)

    subject: str | None = None
    text_body: str | None = None
    html_body: str | None = None

    received_at: datetime | None = None
    sent_at: datetime | None = None

    direction: str
    unread: bool
    has_attachments: bool

    created_at: datetime
    updated_at: datetime


class EmailThreadSummary(BaseModel):
    """Summary information for one inbox thread."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_thread_id: str

    subject: str | None = None
    snippet: str | None = None

    participant_emails: list[str] = Field(default_factory=list)

    last_message_at: datetime | None = None
    unread: bool

    message_count: int = 0

    created_at: datetime
    updated_at: datetime


class EmailThreadListResponse(BaseModel):
    """Paginated thread-list response."""

    items: list[EmailThreadSummary]

    total: int
    page: int
    page_size: int
    total_pages: int


class EmailThreadDetail(BaseModel):
    """A thread with all synchronized messages."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_thread_id: str

    subject: str | None = None
    snippet: str | None = None

    participant_emails: list[str] = Field(default_factory=list)

    last_message_at: datetime | None = None
    unread: bool

    created_at: datetime
    updated_at: datetime

    messages: list[EmailMessageResponse] = Field(
        default_factory=list
    )