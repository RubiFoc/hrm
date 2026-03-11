"""add onboarding checklist templates

Revision ID: 20260310000016
Revises: 20260310000015
Create Date: 2026-03-11 02:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000016"
down_revision = "20260310000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create onboarding checklist template tables."""
    op.create_table(
        "onboarding_templates",
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_staff_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("template_id"),
    )
    op.create_index(
        "ux_onboarding_templates_name",
        "onboarding_templates",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_onboarding_templates_is_active",
        "onboarding_templates",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "onboarding_template_items",
        sa.Column("template_item_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["onboarding_templates.template_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("template_item_id"),
    )
    op.create_index(
        "ux_onboarding_template_items_code",
        "onboarding_template_items",
        ["template_id", "code"],
        unique=True,
    )
    op.create_index(
        "ux_onboarding_template_items_sort_order",
        "onboarding_template_items",
        ["template_id", "sort_order"],
        unique=True,
    )


def downgrade() -> None:
    """Drop onboarding checklist template tables."""
    op.drop_index(
        "ux_onboarding_template_items_sort_order",
        table_name="onboarding_template_items",
    )
    op.drop_index(
        "ux_onboarding_template_items_code",
        table_name="onboarding_template_items",
    )
    op.drop_table("onboarding_template_items")
    op.drop_index("ix_onboarding_templates_is_active", table_name="onboarding_templates")
    op.drop_index("ux_onboarding_templates_name", table_name="onboarding_templates")
    op.drop_table("onboarding_templates")
