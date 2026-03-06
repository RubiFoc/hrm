"""add cv analysis fields to candidate documents

Revision ID: 20260306000008
Revises: 20260305000007
Create Date: 2026-03-06 12:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306000008"
down_revision = "20260305000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add parsed profile, evidence, language, and parse timestamp to CV metadata."""
    op.add_column(
        "candidate_documents",
        sa.Column("parsed_profile_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "candidate_documents",
        sa.Column("evidence_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "candidate_documents",
        sa.Column(
            "detected_language",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "candidate_documents",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_candidate_documents_parsed_at",
        "candidate_documents",
        ["parsed_at"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_documents_candidate_parsed_at",
        "candidate_documents",
        ["candidate_id", "parsed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop CV analysis fields from candidate documents."""
    op.drop_index("ix_candidate_documents_candidate_parsed_at", table_name="candidate_documents")
    op.drop_index("ix_candidate_documents_parsed_at", table_name="candidate_documents")
    op.drop_column("candidate_documents", "parsed_at")
    op.drop_column("candidate_documents", "detected_language")
    op.drop_column("candidate_documents", "evidence_json")
    op.drop_column("candidate_documents", "parsed_profile_json")
