"""Anti-spam policy checks for the public vacancy application endpoint."""

from __future__ import annotations

from fastapi import status

from hrm_backend.vacancies.dao.public_apply_guard_dao import PublicApplyGuardDAO
from hrm_backend.vacancies.schemas.application import (
    PUBLIC_APPLY_REASON_COOLDOWN_ACTIVE,
    PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION,
    PUBLIC_APPLY_REASON_HONEYPOT_TRIGGERED,
)
from hrm_backend.vacancies.services.public_apply_exceptions import PublicApplyRejectedError


class PublicApplyPolicyService:
    """Runs anti-spam guards before creating a public vacancy application."""

    def __init__(
        self,
        *,
        guard_dao: PublicApplyGuardDAO,
        email_cooldown_seconds: int,
        dedup_window_seconds: int,
    ) -> None:
        """Initialize policy dependencies and anti-spam windows.

        Args:
            guard_dao: DAO used for recent submission lookups.
            email_cooldown_seconds: Cooldown window per email+vacancy pair.
            dedup_window_seconds: Deduplication window per vacancy+checksum pair.
        """
        self._guard_dao = guard_dao
        self._email_cooldown_seconds = email_cooldown_seconds
        self._dedup_window_seconds = dedup_window_seconds

    def enforce_honeypot(self, *, website: str | None) -> None:
        """Reject request when honeypot field is filled."""
        if website is None or not website.strip():
            return

        raise PublicApplyRejectedError(
            reason_code=PUBLIC_APPLY_REASON_HONEYPOT_TRIGGERED,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bot submission detected",
        )

    def enforce_email_cooldown(
        self,
        *,
        vacancy_id: str,
        email: str,
    ) -> None:
        """Reject request when recent application exists for email+vacancy pair."""
        if not self._guard_dao.has_recent_submission_for_email(
            vacancy_id=vacancy_id,
            email=email,
            window_seconds=self._email_cooldown_seconds,
        ):
            return

        raise PublicApplyRejectedError(
            reason_code=PUBLIC_APPLY_REASON_COOLDOWN_ACTIVE,
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cooldown active for this email and vacancy. "
                "Please wait before submitting again."
            ),
        )

    def enforce_checksum_dedup(
        self,
        *,
        vacancy_id: str,
        checksum_sha256: str,
    ) -> None:
        """Reject request when checksum was already submitted to the same vacancy."""
        if not self._guard_dao.has_recent_submission_for_checksum(
            vacancy_id=vacancy_id,
            checksum_sha256=checksum_sha256,
            window_seconds=self._dedup_window_seconds,
        ):
            return

        raise PublicApplyRejectedError(
            reason_code=PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION,
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate submission detected for this vacancy",
        )
