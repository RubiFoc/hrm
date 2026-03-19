"""KPI metric registry for reporting snapshots."""

from __future__ import annotations

KPI_METRIC_KEYS: tuple[str, ...] = (
    "vacancies_created_count",
    "candidates_applied_count",
    "interviews_scheduled_count",
    "offers_sent_count",
    "offers_accepted_count",
    "hires_count",
    "onboarding_started_count",
    "onboarding_tasks_completed_count",
    "total_hr_operations_count",
    "automated_hr_operations_count",
    "automated_hr_operations_share_percent",
)
KPI_METRIC_KEY_SET = frozenset(KPI_METRIC_KEYS)


def is_supported_metric(metric_key: str) -> bool:
    """Check whether a metric key is part of the KPI snapshot registry.

    Args:
        metric_key: Metric identifier to validate.

    Returns:
        bool: True when the metric key is supported by KPI snapshots.
    """
    return metric_key in KPI_METRIC_KEY_SET
