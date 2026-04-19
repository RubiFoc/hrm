"""add departments table

Revision ID: 20260406000028
Revises: 20260404000027
Create Date: 2026-04-06 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260406000028"
down_revision = "20260404000027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the departments reference table."""
    op.create_table(
        "departments",
        sa.Column("department_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("department_id"),
    )
    op.create_index("ix_departments_name", "departments", ["name"], unique=True)


def downgrade() -> None:
    """Drop the departments reference table."""
    op.drop_index("ix_departments_name", table_name="departments")
    op.drop_table("departments")
