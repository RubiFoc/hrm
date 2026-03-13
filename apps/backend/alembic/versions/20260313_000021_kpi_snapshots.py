"""Create KPI snapshot storage table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260313000021"
down_revision = "20260313000020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create KPI snapshot table and supporting indexes."""
    op.create_table(
        "kpi_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("metric_value", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint(
            "period_month",
            "metric_key",
            name="ux_kpi_snapshots_period_metric",
        ),
    )
    op.create_index(
        "ix_kpi_snapshots_period_month",
        "kpi_snapshots",
        ["period_month"],
        unique=False,
    )


def downgrade() -> None:
    """Drop KPI snapshot table and supporting indexes."""
    op.drop_index("ix_kpi_snapshots_period_month", table_name="kpi_snapshots")
    op.drop_table("kpi_snapshots")
