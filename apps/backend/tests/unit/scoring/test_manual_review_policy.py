"""Unit tests for low-confidence manual review scoring policy."""

from hrm_backend.scoring.services.manual_review_policy import (
    evaluate_manual_review_requirement,
)


def test_policy_requires_manual_review_below_threshold() -> None:
    """Verify succeeded scores below the threshold require manual review."""
    decision = evaluate_manual_review_requirement(
        status="succeeded",
        confidence=0.69,
        threshold=0.7,
    )

    assert decision.requires_manual_review is True
    assert decision.manual_review_reason == "low_confidence"
    assert decision.confidence_threshold == 0.7


def test_policy_does_not_require_manual_review_at_threshold() -> None:
    """Verify threshold equality does not trigger the strict less-than fallback."""
    decision = evaluate_manual_review_requirement(
        status="succeeded",
        confidence=0.7,
        threshold=0.7,
    )

    assert decision.requires_manual_review is False
    assert decision.manual_review_reason is None
    assert decision.confidence_threshold == 0.7


def test_policy_does_not_require_manual_review_above_threshold() -> None:
    """Verify succeeded scores above the threshold remain on the normal path."""
    decision = evaluate_manual_review_requirement(
        status="succeeded",
        confidence=0.84,
        threshold=0.7,
    )

    assert decision.requires_manual_review is False
    assert decision.manual_review_reason is None
    assert decision.confidence_threshold == 0.7


def test_policy_does_not_require_manual_review_for_non_succeeded_statuses() -> None:
    """Verify queued/running/failed statuses never expose fallback metadata."""
    for status in ("queued", "running", "failed"):
        decision = evaluate_manual_review_requirement(
            status=status,
            confidence=0.1,
            threshold=0.7,
        )

        assert decision.requires_manual_review is False
        assert decision.manual_review_reason is None
        assert decision.confidence_threshold is None


def test_policy_does_not_require_manual_review_when_confidence_is_missing() -> None:
    """Verify missing confidence on succeeded responses stays non-blocking."""
    decision = evaluate_manual_review_requirement(
        status="succeeded",
        confidence=None,
        threshold=0.7,
    )

    assert decision.requires_manual_review is False
    assert decision.manual_review_reason is None
    assert decision.confidence_threshold == 0.7
