"""create cv parsing jobs table

Revision ID: 20260304000006
Revises: 20260304000005
Create Date: 2026-03-04 16:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304000006"
down_revision = "20260304000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create async CV parsing job table with lifecycle indexes."""
    op.create_table(
        "cv_parsing_jobs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["candidate_documents.document_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_cv_parsing_jobs_status", "cv_parsing_jobs", ["status"], unique=False)
    op.create_index("ix_cv_parsing_jobs_queued_at", "cv_parsing_jobs", ["queued_at"], unique=False)
    op.create_index(
        "ix_cv_parsing_jobs_candidate_id",
        "cv_parsing_jobs",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_cv_parsing_jobs_document_id",
        "cv_parsing_jobs",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop async CV parsing job table and supporting indexes."""
    op.drop_index("ix_cv_parsing_jobs_document_id", table_name="cv_parsing_jobs")
    op.drop_index("ix_cv_parsing_jobs_candidate_id", table_name="cv_parsing_jobs")
    op.drop_index("ix_cv_parsing_jobs_queued_at", table_name="cv_parsing_jobs")
    op.drop_index("ix_cv_parsing_jobs_status", table_name="cv_parsing_jobs")
    op.drop_table("cv_parsing_jobs")
