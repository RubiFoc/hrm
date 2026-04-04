"""add employee directory privacy flags and avatars

Revision ID: 20260327000026
Revises: 20260327000025
Create Date: 2026-03-27 12:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260327000026"
down_revision = "20260327000025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add employee directory privacy flags and avatar metadata."""
    op.add_column(
        "employee_profiles",
        sa.Column("department", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column("position_title", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column("manager", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column("birthday_day_month", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "employee_profiles",
        sa.Column(
            "is_phone_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "employee_profiles",
        sa.Column(
            "is_email_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "employee_profiles",
        sa.Column(
            "is_birthday_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "employee_profiles",
        sa.Column(
            "is_dismissed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_table(
        "employee_profile_avatars",
        sa.Column("avatar_id", sa.String(length=36), nullable=False),
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("avatar_id"),
    )
    op.create_index(
        "ix_employee_profile_avatars_employee_id",
        "employee_profile_avatars",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_profile_avatars_object_key",
        "employee_profile_avatars",
        ["object_key"],
        unique=True,
    )
    op.create_index(
        "ix_employee_profile_avatars_employee_active",
        "employee_profile_avatars",
        ["employee_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Drop employee directory privacy flags and avatar metadata."""
    op.drop_index(
        "ix_employee_profile_avatars_employee_active",
        table_name="employee_profile_avatars",
    )
    op.drop_index(
        "ix_employee_profile_avatars_object_key",
        table_name="employee_profile_avatars",
    )
    op.drop_index(
        "ix_employee_profile_avatars_employee_id",
        table_name="employee_profile_avatars",
    )
    op.drop_table("employee_profile_avatars")
    op.drop_column("employee_profiles", "is_dismissed")
    op.drop_column("employee_profiles", "is_birthday_visible")
    op.drop_column("employee_profiles", "is_email_visible")
    op.drop_column("employee_profiles", "is_phone_visible")
    op.drop_column("employee_profiles", "birthday_day_month")
    op.drop_column("employee_profiles", "manager")
    op.drop_column("employee_profiles", "position_title")
    op.drop_column("employee_profiles", "department")
