"""add interview feedback table

Revision ID: 20260310000011
Revises: 20260309000010
Create Date: 2026-03-10 21:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000011"
down_revision = "20260309000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create structured interview feedback table."""
    op.create_table(
        "interview_feedback",
        sa.Column("feedback_id", sa.String(length=36), nullable=False),
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column("schedule_version", sa.Integer(), nullable=False),
        sa.Column("interviewer_staff_id", sa.String(length=36), nullable=False),
        sa.Column("requirements_match_score", sa.Integer(), nullable=False),
        sa.Column("communication_score", sa.Integer(), nullable=False),
        sa.Column("problem_solving_score", sa.Integer(), nullable=False),
        sa.Column("collaboration_score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("strengths_note", sa.Text(), nullable=False),
        sa.Column("concerns_note", sa.Text(), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["interviews.interview_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index(
        "ix_interview_feedback_interview_id",
        "interview_feedback",
        ["interview_id"],
        unique=False,
    )
    op.create_index(
        "ix_interview_feedback_schedule_version",
        "interview_feedback",
        ["schedule_version"],
        unique=False,
    )
    op.create_index(
        "ux_interview_feedback_interviewer_version",
        "interview_feedback",
        ["interview_id", "schedule_version", "interviewer_staff_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop structured interview feedback table."""
    op.drop_index(
        "ux_interview_feedback_interviewer_version",
        table_name="interview_feedback",
    )
    op.drop_index(
        "ix_interview_feedback_schedule_version",
        table_name="interview_feedback",
    )
    op.drop_index(
        "ix_interview_feedback_interview_id",
        table_name="interview_feedback",
    )
    op.drop_table("interview_feedback")
