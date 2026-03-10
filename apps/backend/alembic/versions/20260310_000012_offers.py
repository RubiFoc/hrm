"""add offer lifecycle table

Revision ID: 20260310000012
Revises: 20260310000011
Create Date: 2026-03-10 23:20:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000012"
down_revision = "20260310000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persisted offer lifecycle table."""
    op.create_table(
        "offers",
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("terms_summary", sa.Text(), nullable=True),
        sa.Column("proposed_start_date", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by_staff_id", sa.String(length=36), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decision_recorded_by_staff_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("offer_id"),
    )
    op.create_index(
        "ux_offers_vacancy_candidate",
        "offers",
        ["vacancy_id", "candidate_id"],
        unique=True,
    )
    op.create_index(
        "ix_offers_status",
        "offers",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop persisted offer lifecycle table."""
    op.drop_index("ix_offers_status", table_name="offers")
    op.drop_index("ux_offers_vacancy_candidate", table_name="offers")
    op.drop_table("offers")
