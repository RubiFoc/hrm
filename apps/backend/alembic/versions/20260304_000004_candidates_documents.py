"""create candidate profiles and documents tables

Revision ID: 20260304000004
Revises: 20260304000003
Create Date: 2026-03-04 16:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304000004"
down_revision = "20260304000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create candidate profile and document metadata tables."""
    op.create_table(
        "candidate_profiles",
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("owner_subject_id", sa.String(length=128), nullable=False),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("location", sa.String(length=256), nullable=True),
        sa.Column("current_title", sa.String(length=256), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    op.create_index(
        "ix_candidate_profiles_owner_subject_id",
        "candidate_profiles",
        ["owner_subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_profiles_email",
        "candidate_profiles",
        ["email"],
        unique=False,
    )

    op.create_table(
        "candidate_documents",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(
        "ix_candidate_documents_candidate_id",
        "candidate_documents",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_documents_object_key",
        "candidate_documents",
        ["object_key"],
        unique=True,
    )
    op.create_index(
        "ix_candidate_documents_candidate_active",
        "candidate_documents",
        ["candidate_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Drop candidate profile and document metadata tables."""
    op.drop_index("ix_candidate_documents_candidate_active", table_name="candidate_documents")
    op.drop_index("ix_candidate_documents_object_key", table_name="candidate_documents")
    op.drop_index("ix_candidate_documents_candidate_id", table_name="candidate_documents")
    op.drop_table("candidate_documents")

    op.drop_index("ix_candidate_profiles_email", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_owner_subject_id", table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
