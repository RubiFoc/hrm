"""add employee profile avatar and dismissal fields

Revision ID: 20260327000025
Revises: 20260319000024
Create Date: 2026-03-27 10:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260327000025"
down_revision = "20260319000024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add avatar metadata and dismissal marker to employee profiles."""
    op.add_column(
        "employee_profiles",
        sa.Column("avatar_object_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column("avatar_mime_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column(
            "is_dismissed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_employee_profiles_is_dismissed",
        "employee_profiles",
        ["is_dismissed"],
        unique=False,
    )
    op.alter_column(
        "employee_profiles",
        "is_dismissed",
        server_default=None,
    )


def downgrade() -> None:
    """Drop avatar metadata and dismissal marker from employee profiles."""
    op.drop_index("ix_employee_profiles_is_dismissed", table_name="employee_profiles")
    op.drop_column("employee_profiles", "is_dismissed")
    op.drop_column("employee_profiles", "avatar_updated_at")
    op.drop_column("employee_profiles", "avatar_mime_type")
    op.drop_column("employee_profiles", "avatar_object_key")
