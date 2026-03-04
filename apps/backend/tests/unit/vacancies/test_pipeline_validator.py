"""Unit tests for canonical pipeline transition validator."""

from __future__ import annotations

from hrm_backend.vacancies.utils.pipeline import is_transition_allowed


def test_pipeline_validator_allows_canonical_chain() -> None:
    """Verify canonical transitions are allowed."""
    assert is_transition_allowed(None, "applied") is True
    assert is_transition_allowed("applied", "screening") is True
    assert is_transition_allowed("screening", "shortlist") is True
    assert is_transition_allowed("shortlist", "interview") is True
    assert is_transition_allowed("interview", "offer") is True
    assert is_transition_allowed("offer", "hired") is True
    assert is_transition_allowed("offer", "rejected") is True


def test_pipeline_validator_rejects_non_canonical_transitions() -> None:
    """Verify out-of-order or terminal transitions are rejected."""
    assert is_transition_allowed(None, "screening") is False
    assert is_transition_allowed("applied", "offer") is False
    assert is_transition_allowed("screening", "offer") is False
    assert is_transition_allowed("hired", "offer") is False
    assert is_transition_allowed("rejected", "applied") is False
