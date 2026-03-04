"""create staff auth tables

Revision ID: 20260304000003
Revises: 20260304000002
Create Date: 2026-03-04 23:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304000003"
down_revision = "20260304000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create staff account and employee registration key tables."""
    op.create_table(
        "staff_accounts",
        sa.Column("staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("staff_id"),
    )
    op.create_index("ix_staff_accounts_login", "staff_accounts", ["login"], unique=True)
    op.create_index("ix_staff_accounts_email", "staff_accounts", ["email"], unique=True)

    op.create_table(
        "employee_registration_keys",
        sa.Column("key_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("employee_key", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("target_role", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("key_id"),
    )
    op.create_index(
        "ix_employee_registration_keys_employee_key",
        "employee_registration_keys",
        ["employee_key"],
        unique=True,
    )
    op.create_index(
        "ix_employee_registration_keys_expires_at",
        "employee_registration_keys",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop staff auth tables."""
    op.drop_index(
        "ix_employee_registration_keys_expires_at",
        table_name="employee_registration_keys",
    )
    op.drop_index(
        "ix_employee_registration_keys_employee_key",
        table_name="employee_registration_keys",
    )
    op.drop_table("employee_registration_keys")
    op.drop_index("ix_staff_accounts_email", table_name="staff_accounts")
    op.drop_index("ix_staff_accounts_login", table_name="staff_accounts")
    op.drop_table("staff_accounts")
