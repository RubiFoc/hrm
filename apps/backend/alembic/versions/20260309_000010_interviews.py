"""add interview scheduling tables

Revision ID: 20260309000010
Revises: 20260309000009
Create Date: 2026-03-09 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260309000010"
down_revision = "20260309000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create interview lifecycle and calendar-binding tables."""
    op.create_table(
        "interviews",
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("calendar_sync_status", sa.String(length=32), nullable=False),
        sa.Column("schedule_version", sa.Integer(), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=128), nullable=False),
        sa.Column("location_kind", sa.String(length=32), nullable=False),
        sa.Column("location_details", sa.Text(), nullable=True),
        sa.Column("interviewer_staff_ids_json", sa.JSON(), nullable=False),
        sa.Column("calendar_event_id", sa.String(length=512), nullable=True),
        sa.Column("candidate_token_nonce", sa.String(length=128), nullable=True),
        sa.Column("candidate_token_hash", sa.String(length=64), nullable=True),
        sa.Column("candidate_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_response_status", sa.String(length=32), nullable=False),
        sa.Column("candidate_response_note", sa.Text(), nullable=True),
        sa.Column("cancelled_by", sa.String(length=32), nullable=True),
        sa.Column("cancel_reason_code", sa.String(length=128), nullable=True),
        sa.Column("calendar_sync_reason_code", sa.String(length=128), nullable=True),
        sa.Column("calendar_sync_error_detail", sa.Text(), nullable=True),
        sa.Column("created_by_staff_id", sa.String(length=36), nullable=False),
        sa.Column("updated_by_staff_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.vacancy_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("interview_id"),
    )
    op.create_index("ix_interviews_vacancy_id", "interviews", ["vacancy_id"], unique=False)
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"], unique=False)
    op.create_index("ix_interviews_status", "interviews", ["status"], unique=False)
    op.create_index(
        "ix_interviews_calendar_sync_status",
        "interviews",
        ["calendar_sync_status"],
        unique=False,
    )
    op.create_index(
        "ix_interviews_candidate_token_hash",
        "interviews",
        ["candidate_token_hash"],
        unique=False,
    )
    op.create_index(
        "ux_interviews_one_active_per_pair",
        "interviews",
        ["vacancy_id", "candidate_id"],
        unique=True,
        sqlite_where=sa.text("status != 'cancelled'"),
        postgresql_where=sa.text("status != 'cancelled'"),
    )

    op.create_table(
        "interview_calendar_bindings",
        sa.Column("binding_id", sa.String(length=36), nullable=False),
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column("interviewer_staff_id", sa.String(length=36), nullable=False),
        sa.Column("calendar_id", sa.String(length=512), nullable=False),
        sa.Column("calendar_event_id", sa.String(length=512), nullable=False),
        sa.Column("schedule_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.interview_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("binding_id"),
    )
    op.create_index(
        "ix_interview_calendar_bindings_interview_id",
        "interview_calendar_bindings",
        ["interview_id"],
        unique=False,
    )
    op.create_index(
        "ux_interview_calendar_bindings_interviewer",
        "interview_calendar_bindings",
        ["interview_id", "interviewer_staff_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop interview scheduling tables."""
    op.drop_index(
        "ux_interview_calendar_bindings_interviewer",
        table_name="interview_calendar_bindings",
    )
    op.drop_index(
        "ix_interview_calendar_bindings_interview_id",
        table_name="interview_calendar_bindings",
    )
    op.drop_table("interview_calendar_bindings")

    op.drop_index("ux_interviews_one_active_per_pair", table_name="interviews")
    op.drop_index("ix_interviews_candidate_token_hash", table_name="interviews")
    op.drop_index("ix_interviews_calendar_sync_status", table_name="interviews")
    op.drop_index("ix_interviews_status", table_name="interviews")
    op.drop_index("ix_interviews_candidate_id", table_name="interviews")
    op.drop_index("ix_interviews_vacancy_id", table_name="interviews")
    op.drop_table("interviews")
