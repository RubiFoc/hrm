"""add onboarding runs table

Revision ID: 20260310000015
Revises: 20260310000014
Create Date: 2026-03-11 01:15:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000015"
down_revision = "20260310000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create minimal onboarding-start persistence table."""
    op.create_table(
        "onboarding_runs",
        sa.Column("onboarding_id", sa.String(length=36), nullable=False),
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("hire_conversion_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_by_staff_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hire_conversion_id"],
            ["hire_conversions.conversion_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("onboarding_id"),
    )
    op.create_index(
        "ux_onboarding_runs_employee",
        "onboarding_runs",
        ["employee_id"],
        unique=True,
    )
    op.create_index(
        "ix_onboarding_runs_status",
        "onboarding_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop minimal onboarding-start persistence table."""
    op.drop_index("ix_onboarding_runs_status", table_name="onboarding_runs")
    op.drop_index("ux_onboarding_runs_employee", table_name="onboarding_runs")
    op.drop_table("onboarding_runs")
