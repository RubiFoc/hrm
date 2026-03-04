"""initial bootstrap

Revision ID: 20260304000001
Revises:
Create Date: 2026-03-04 03:40:00
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "20260304000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply initial migration bootstrap without domain tables."""
    pass


def downgrade() -> None:
    """Rollback initial migration bootstrap."""
    pass
