"""add vacancy hiring manager ownership field

Revision ID: 20260312000019
Revises: 20260310000018
Create Date: 2026-03-12 10:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260312000019"
down_revision = "20260310000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable manager ownership to vacancies for scoped manager workspace reads."""
    op.add_column(
        "vacancies",
        sa.Column("hiring_manager_staff_id", sa.Uuid(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_vacancies_hiring_manager_staff",
        "vacancies",
        "staff_accounts",
        ["hiring_manager_staff_id"],
        ["staff_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_vacancies_hiring_manager_staff_id",
        "vacancies",
        ["hiring_manager_staff_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop manager ownership from vacancies."""
    op.drop_index("ix_vacancies_hiring_manager_staff_id", table_name="vacancies")
    op.drop_constraint(
        "fk_vacancies_hiring_manager_staff",
        "vacancies",
        type_="foreignkey",
    )
    op.drop_column("vacancies", "hiring_manager_staff_id")
