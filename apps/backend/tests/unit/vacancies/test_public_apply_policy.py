"""Unit tests for public apply anti-spam policy service."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from hrm_backend.vacancies.schemas.application import (
    PUBLIC_APPLY_REASON_COOLDOWN_ACTIVE,
    PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION,
    PUBLIC_APPLY_REASON_HONEYPOT_TRIGGERED,
)
from hrm_backend.vacancies.services.public_apply_exceptions import PublicApplyRejectedError
from hrm_backend.vacancies.services.public_apply_policy import PublicApplyPolicyService


@dataclass
class _GuardDAOStub:
    email_recent: bool = False
    checksum_recent: bool = False

    def has_recent_submission_for_email(
        self,
        *,
        vacancy_id: str,
        email: str,
        window_seconds: int,
    ) -> bool:
        del vacancy_id, email, window_seconds
        return self.email_recent

    def has_recent_submission_for_checksum(
        self,
        *,
        vacancy_id: str,
        checksum_sha256: str,
        window_seconds: int,
    ) -> bool:
        del vacancy_id, checksum_sha256, window_seconds
        return self.checksum_recent


def test_honeypot_submission_is_rejected() -> None:
    """Verify non-empty honeypot field triggers blocked response."""
    policy = PublicApplyPolicyService(
        guard_dao=_GuardDAOStub(),
        email_cooldown_seconds=60,
        dedup_window_seconds=24 * 60 * 60,
    )

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        policy.enforce_honeypot(website="https://spam.invalid")

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_HONEYPOT_TRIGGERED
    assert exc_info.value.status_code == 422


def test_email_cooldown_rejects_recent_submission() -> None:
    """Verify cooldown guard returns explicit cooldown reason code."""
    policy = PublicApplyPolicyService(
        guard_dao=_GuardDAOStub(email_recent=True),
        email_cooldown_seconds=60,
        dedup_window_seconds=24 * 60 * 60,
    )

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        policy.enforce_email_cooldown(vacancy_id="vacancy-1", email="user@example.com")

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_COOLDOWN_ACTIVE
    assert exc_info.value.status_code == 409


def test_checksum_dedup_rejects_duplicate_submission() -> None:
    """Verify checksum dedup guard rejects duplicate requests."""
    policy = PublicApplyPolicyService(
        guard_dao=_GuardDAOStub(checksum_recent=True),
        email_cooldown_seconds=60,
        dedup_window_seconds=24 * 60 * 60,
    )

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        policy.enforce_checksum_dedup(vacancy_id="vacancy-1", checksum_sha256="a" * 64)

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION
    assert exc_info.value.status_code == 409


def test_policy_passes_when_no_blocking_conditions_met() -> None:
    """Verify policy allows request when honeypot/cooldown/dedup checks are clear."""
    policy = PublicApplyPolicyService(
        guard_dao=_GuardDAOStub(),
        email_cooldown_seconds=60,
        dedup_window_seconds=24 * 60 * 60,
    )

    policy.enforce_honeypot(website=None)
    policy.enforce_email_cooldown(vacancy_id="vacancy-1", email="user@example.com")
    policy.enforce_checksum_dedup(vacancy_id="vacancy-1", checksum_sha256="a" * 64)
