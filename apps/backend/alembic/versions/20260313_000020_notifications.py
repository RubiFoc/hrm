"""Create recipient-scoped in-app notifications table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260313000020"
down_revision = "20260312000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the notifications table and supporting indexes."""
    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("recipient_role", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipient_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("notification_id"),
        sa.UniqueConstraint(
            "recipient_staff_id",
            "dedupe_key",
            name="ux_notifications_recipient_dedupe",
        ),
    )
    op.create_index(
        "ix_notifications_recipient_created_at",
        "notifications",
        ["recipient_staff_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_recipient_read_at",
        "notifications",
        ["recipient_staff_id", "read_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the notifications table and supporting indexes."""
    op.drop_index("ix_notifications_recipient_read_at", table_name="notifications")
    op.drop_index("ix_notifications_recipient_created_at", table_name="notifications")
    op.drop_table("notifications")
