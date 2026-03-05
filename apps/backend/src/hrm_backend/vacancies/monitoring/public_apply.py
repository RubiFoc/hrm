"""In-process counters and structured logs for public apply anti-abuse monitoring."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping
from json import dumps
from logging import getLogger
from threading import Lock
from time import time

from hrm_backend.vacancies.schemas.application import PublicApplyReasonCode

_logger = getLogger(__name__)
_lock = Lock()
_counters: Counter[str] = Counter()
_blocked_timestamps: deque[float] = deque()


def record_public_apply_success(
    *,
    correlation_id: str | None,
    vacancy_id: str,
) -> None:
    """Record successful public apply request metrics and structured log."""
    with _lock:
        _counters["success"] += 1

    _logger.info(
        dumps(
            {
                "event": "vacancy_apply_public",
                "result": "success",
                "vacancy_id": vacancy_id,
                "correlation_id": correlation_id,
            },
            sort_keys=True,
        )
    )


def record_public_apply_blocked(
    *,
    correlation_id: str | None,
    vacancy_id: str,
    reason_code: PublicApplyReasonCode,
    blocked_alert_threshold_per_minute: int,
) -> None:
    """Record blocked request metrics, structured log, and anomaly warning signal."""
    now = time()
    with _lock:
        _counters["blocked_total"] += 1
        _counters[f"blocked:{reason_code}"] += 1
        _blocked_timestamps.append(now)
        while _blocked_timestamps and (now - _blocked_timestamps[0]) > 60:
            _blocked_timestamps.popleft()
        blocked_per_minute = len(_blocked_timestamps)

    _logger.info(
        dumps(
            {
                "event": "vacancy_apply_public",
                "result": "blocked",
                "reason_code": reason_code,
                "vacancy_id": vacancy_id,
                "correlation_id": correlation_id,
                "blocked_per_minute": blocked_per_minute,
            },
            sort_keys=True,
        )
    )

    if blocked_alert_threshold_per_minute <= 0:
        return
    if blocked_per_minute < blocked_alert_threshold_per_minute:
        return

    _logger.warning(
        dumps(
            {
                "event": "vacancy_apply_public_blocked_anomaly",
                "blocked_per_minute": blocked_per_minute,
                "threshold_per_minute": blocked_alert_threshold_per_minute,
                "correlation_id": correlation_id,
                "vacancy_id": vacancy_id,
            },
            sort_keys=True,
        )
    )


def snapshot_public_apply_metrics() -> Mapping[str, int]:
    """Return in-process counters snapshot (used by tests and diagnostics)."""
    with _lock:
        return dict(_counters)
