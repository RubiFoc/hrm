"""add employee profile self-service identity link

Revision ID: 20260310000018
Revises: 20260310000017
Create Date: 2026-03-11 05:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000018"
down_revision = "20260310000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable staff-account link used by employee self-service onboarding."""
    op.add_column(
        "employee_profiles",
        sa.Column("staff_account_id", sa.Uuid(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_employee_profiles_staff_account",
        "employee_profiles",
        "staff_accounts",
        ["staff_account_id"],
        ["staff_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ux_employee_profiles_staff_account",
        "employee_profiles",
        ["staff_account_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop employee self-service identity link from employee profiles."""
    op.drop_index("ux_employee_profiles_staff_account", table_name="employee_profiles")
    op.drop_constraint(
        "fk_employee_profiles_staff_account",
        "employee_profiles",
        type_="foreignkey",
    )
    op.drop_column("employee_profiles", "staff_account_id")
