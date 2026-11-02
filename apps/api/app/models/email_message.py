import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    __table_args__ = (
        UniqueConstraint(
            "gmail_connection_id",
            "provider_message_id",
            name="uq_email_message_provider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    gmail_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "gmail_connections.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "email_threads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    provider_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    internet_message_id: Mapped[str | None] = mapped_column(
        String(998),
        nullable=True,
        index=True,
    )

    in_reply_to: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    references_header: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sender_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    sender_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )

    recipient_emails: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    cc_emails: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    subject: Mapped[str | None] = mapped_column(
        String(998),
        nullable=True,
        index=True,
    )

    text_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    html_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    unread: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    has_attachments: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    raw_headers: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )