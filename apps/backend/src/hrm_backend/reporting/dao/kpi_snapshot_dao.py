"""Data-access helpers for KPI snapshot persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from hrm_backend.reporting.models.kpi_snapshot import KpiSnapshot


class KpiSnapshotDAO:
    """Persist and query monthly KPI snapshots."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def list_by_period_month(self, *, period_month: date) -> list[KpiSnapshot]:
        """Return KPI snapshot rows for the provided month.

        Args:
            period_month: First day of the month to read.

        Returns:
            list[KpiSnapshot]: Snapshot rows ordered by metric key.
        """
        return list(
            self._session.query(KpiSnapshot)
            .filter(KpiSnapshot.period_month == period_month)
            .order_by(KpiSnapshot.metric_key.asc(), KpiSnapshot.snapshot_id.asc())
            .all()
        )

    def replace_monthly_snapshots(
        self,
        *,
        period_month: date,
        snapshots: Sequence[KpiSnapshot],
        commit: bool = True,
    ) -> None:
        """Replace all KPI snapshots for one month in a single transaction.

        Args:
            period_month: First day of the month to replace.
            snapshots: Snapshot rows to insert.
            commit: When True, commit immediately; otherwise flush for external transaction control.
        """
        self._session.query(KpiSnapshot).filter(
            KpiSnapshot.period_month == period_month
        ).delete(synchronize_session=False)
        for snapshot in snapshots:
            self._session.add(snapshot)
        if commit:
            self._session.commit()
            return

        self._session.flush()
