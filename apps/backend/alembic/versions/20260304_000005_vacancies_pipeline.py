"""create vacancies and pipeline transitions tables

Revision ID: 20260304000005
Revises: 20260304000004
Create Date: 2026-03-04 16:15:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304000005"
down_revision = "20260304000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create vacancies and append-only pipeline transition history tables."""
    op.create_table(
        "vacancies",
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("vacancy_id"),
    )
    op.create_index("ix_vacancies_status", "vacancies", ["status"], unique=False)
    op.create_index("ix_vacancies_created_at", "vacancies", ["created_at"], unique=False)

    op.create_table(
        "pipeline_transitions",
        sa.Column("transition_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("from_stage", sa.String(length=32), nullable=True),
        sa.Column("to_stage", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_sub", sa.String(length=128), nullable=False),
        sa.Column("changed_by_role", sa.String(length=64), nullable=False),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.vacancy_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transition_id"),
    )
    op.create_index(
        "ix_pipeline_transitions_vacancy_candidate_time",
        "pipeline_transitions",
        ["vacancy_id", "candidate_id", "transitioned_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop vacancies and pipeline transition history tables."""
    op.drop_index(
        "ix_pipeline_transitions_vacancy_candidate_time",
        table_name="pipeline_transitions",
    )
    op.drop_table("pipeline_transitions")

    op.drop_index("ix_vacancies_created_at", table_name="vacancies")
    op.drop_index("ix_vacancies_status", table_name="vacancies")
    op.drop_table("vacancies")
