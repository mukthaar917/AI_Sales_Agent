"""create quotations tables

Revision ID: a2aa7db8d3c6
Revises: 678e2fd926f7
Create Date: 2026-07-29 10:57:30.734068
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2aa7db8d3c6"
down_revision: Union[str, Sequence[str], None] = "678e2fd926f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "quotations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "quotation_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "reviewed",
                "approved",
                "sent",
                "accepted",
                "rejected",
                "expired",
                "cancelled",
                name="quotation_status",
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "issue_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "expiry_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="USD",
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "tax_amount",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "terms",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "quotation_number",
            name="uq_quotation_number",
        ),
    )

    op.create_index(
        op.f("ix_quotations_created_by"),
        "quotations",
        ["created_by"],
        unique=False,
    )

    op.create_index(
        op.f("ix_quotations_customer_id"),
        "quotations",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_quotations_organization_id"),
        "quotations",
        ["organization_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_quotations_quotation_number"),
        "quotations",
        ["quotation_number"],
        unique=False,
    )

    op.create_table(
        "quotation_items",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "quotation_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "unit",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "discount_rate",
            sa.Numeric(
                precision=5,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "tax_rate",
            sa.Numeric(
                precision=5,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "tax_amount",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "line_total",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["quotation_id"],
            ["quotations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_quotation_items_product_id"),
        "quotation_items",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_quotation_items_quotation_id"),
        "quotation_items",
        ["quotation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_quotation_items_quotation_id"),
        table_name="quotation_items",
    )

    op.drop_index(
        op.f("ix_quotation_items_product_id"),
        table_name="quotation_items",
    )

    op.drop_table("quotation_items")

    op.drop_index(
        op.f("ix_quotations_quotation_number"),
        table_name="quotations",
    )

    op.drop_index(
        op.f("ix_quotations_organization_id"),
        table_name="quotations",
    )

    op.drop_index(
        op.f("ix_quotations_customer_id"),
        table_name="quotations",
    )

    op.drop_index(
        op.f("ix_quotations_created_by"),
        table_name="quotations",
    )

    op.drop_table("quotations")

    sa.Enum(
        name="quotation_status",
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )