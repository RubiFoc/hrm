"""add hire conversion handoff table

Revision ID: 20260310000013
Revises: 20260310000012
Create Date: 2026-03-10 23:55:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000013"
down_revision = "20260310000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable hire-conversion handoff table."""
    op.create_table(
        "hire_conversions",
        sa.Column("conversion_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("hired_transition_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("candidate_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("offer_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("converted_by_staff_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.vacancy_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.offer_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hired_transition_id"],
            ["pipeline_transitions.transition_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("conversion_id"),
    )
    op.create_index(
        "ux_hire_conversions_vacancy_candidate",
        "hire_conversions",
        ["vacancy_id", "candidate_id"],
        unique=True,
    )
    op.create_index(
        "ux_hire_conversions_hired_transition",
        "hire_conversions",
        ["hired_transition_id"],
        unique=True,
    )
    op.create_index(
        "ix_hire_conversions_status",
        "hire_conversions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop durable hire-conversion handoff table."""
    op.drop_index("ix_hire_conversions_status", table_name="hire_conversions")
    op.drop_index("ux_hire_conversions_hired_transition", table_name="hire_conversions")
    op.drop_index("ux_hire_conversions_vacancy_candidate", table_name="hire_conversions")
    op.drop_table("hire_conversions")
