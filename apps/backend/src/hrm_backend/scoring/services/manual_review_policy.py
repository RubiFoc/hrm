"""Policy helpers for recruiter-facing match score fallback decisions.

This module evaluates whether a successful score should be treated only as an
assistive signal and echoed back with additive manual-review metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from hrm_backend.scoring.schemas.match_scoring import (
    MatchScoreManualReviewReason,
    MatchScoringStatus,
)


@dataclass(frozen=True, slots=True)
class ManualReviewDecision:
    """Immutable result of low-confidence fallback evaluation.

    Attributes:
        requires_manual_review:
            Whether the recruiter should treat the score as assistive only.
        manual_review_reason:
            Stable reason code returned to API clients when manual review is required.
        confidence_threshold:
            Configured confidence threshold echoed only for succeeded responses.

    Side Effects:
        None.
    """

    requires_manual_review: bool
    manual_review_reason: MatchScoreManualReviewReason | None
    confidence_threshold: float | None


def evaluate_manual_review_requirement(
    *,
    status: MatchScoringStatus,
    confidence: float | None,
    threshold: float,
) -> ManualReviewDecision:
    """Evaluate whether one score response requires manual review.

    Args:
        status:
            Current persisted scoring lifecycle state.
        confidence:
            Optional model confidence stored on the score artifact.
        threshold:
            Configured strict low-confidence cutoff in the inclusive 0..1 range.

    Returns:
        ManualReviewDecision carrying API-ready manual-review flags and threshold echo.

    Raises:
        Does not raise exceptions.

    Side Effects:
        None.
    """

    if status != "succeeded":
        return ManualReviewDecision(
            requires_manual_review=False,
            manual_review_reason=None,
            confidence_threshold=None,
        )

    if confidence is None or confidence >= threshold:
        return ManualReviewDecision(
            requires_manual_review=False,
            manual_review_reason=None,
            confidence_threshold=threshold,
        )

    return ManualReviewDecision(
        requires_manual_review=True,
        manual_review_reason="low_confidence",
        confidence_threshold=threshold,
    )
