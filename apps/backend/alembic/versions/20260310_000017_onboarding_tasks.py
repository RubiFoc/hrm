"""add onboarding tasks

Revision ID: 20260310000017
Revises: 20260310000016
Create Date: 2026-03-11 03:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000017"
down_revision = "20260310000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create materialized onboarding task table."""
    op.create_table(
        "onboarding_tasks",
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("onboarding_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("template_item_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_role", sa.String(length=32), nullable=True),
        sa.Column("assigned_staff_id", sa.String(length=36), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["onboarding_id"],
            ["onboarding_runs.onboarding_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(
        "ux_onboarding_tasks_onboarding_code",
        "onboarding_tasks",
        ["onboarding_id", "code"],
        unique=True,
    )
    op.create_index(
        "ix_onboarding_tasks_onboarding",
        "onboarding_tasks",
        ["onboarding_id"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_tasks_status",
        "onboarding_tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_tasks_due_at",
        "onboarding_tasks",
        ["due_at"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_tasks_assigned_staff",
        "onboarding_tasks",
        ["assigned_staff_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop materialized onboarding task table."""
    op.drop_index("ix_onboarding_tasks_assigned_staff", table_name="onboarding_tasks")
    op.drop_index("ix_onboarding_tasks_due_at", table_name="onboarding_tasks")
    op.drop_index("ix_onboarding_tasks_status", table_name="onboarding_tasks")
    op.drop_index("ix_onboarding_tasks_onboarding", table_name="onboarding_tasks")
    op.drop_index("ux_onboarding_tasks_onboarding_code", table_name="onboarding_tasks")
    op.drop_table("onboarding_tasks")
