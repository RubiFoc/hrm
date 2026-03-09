"""add match scoring jobs and score artifacts

Revision ID: 20260309000009
Revises: 20260306000008
Create Date: 2026-03-09 14:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260309000009"
down_revision = "20260306000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create scoring job and score artifact tables."""
    op.create_table(
        "match_scoring_jobs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profiles.candidate_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["candidate_documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.vacancy_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_match_scoring_jobs_status",
        "match_scoring_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_match_scoring_jobs_queued_at",
        "match_scoring_jobs",
        ["queued_at"],
        unique=False,
    )
    op.create_index(
        "ix_match_scoring_jobs_vacancy_id",
        "match_scoring_jobs",
        ["vacancy_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_scoring_jobs_candidate_id",
        "match_scoring_jobs",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_scoring_jobs_document_id",
        "match_scoring_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_scoring_jobs_vacancy_candidate",
        "match_scoring_jobs",
        ["vacancy_id", "candidate_id"],
        unique=False,
    )

    op.create_table(
        "match_score_artifacts",
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("matched_requirements_json", sa.JSON(), nullable=False),
        sa.Column("missing_requirements_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profiles.candidate_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["candidate_documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["match_scoring_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.vacancy_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        "ix_match_score_artifacts_job_id",
        "match_score_artifacts",
        ["job_id"],
        unique=True,
    )
    op.create_index(
        "ix_match_score_artifacts_vacancy_id",
        "match_score_artifacts",
        ["vacancy_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_score_artifacts_candidate_id",
        "match_score_artifacts",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_score_artifacts_document_id",
        "match_score_artifacts",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_match_score_artifacts_vacancy_candidate_scored_at",
        "match_score_artifacts",
        ["vacancy_id", "candidate_id", "scored_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop scoring job and score artifact tables."""
    op.drop_index(
        "ix_match_score_artifacts_vacancy_candidate_scored_at",
        table_name="match_score_artifacts",
    )
    op.drop_index("ix_match_score_artifacts_document_id", table_name="match_score_artifacts")
    op.drop_index("ix_match_score_artifacts_candidate_id", table_name="match_score_artifacts")
    op.drop_index("ix_match_score_artifacts_vacancy_id", table_name="match_score_artifacts")
    op.drop_index("ix_match_score_artifacts_job_id", table_name="match_score_artifacts")
    op.drop_table("match_score_artifacts")

    op.drop_index("ix_match_scoring_jobs_vacancy_candidate", table_name="match_scoring_jobs")
    op.drop_index("ix_match_scoring_jobs_document_id", table_name="match_scoring_jobs")
    op.drop_index("ix_match_scoring_jobs_candidate_id", table_name="match_scoring_jobs")
    op.drop_index("ix_match_scoring_jobs_vacancy_id", table_name="match_scoring_jobs")
    op.drop_index("ix_match_scoring_jobs_queued_at", table_name="match_scoring_jobs")
    op.drop_index("ix_match_scoring_jobs_status", table_name="match_scoring_jobs")
    op.drop_table("match_scoring_jobs")
