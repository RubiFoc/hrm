"""Unit tests for pure offer lifecycle helpers."""

from hrm_backend.vacancies.utils.offers import (
    OFFER_REASON_ALREADY_ACCEPTED,
    OFFER_REASON_ALREADY_DECLINED,
    OFFER_REASON_ALREADY_SENT,
    OFFER_REASON_NOT_ACCEPTED,
    OFFER_REASON_NOT_DECLINED,
    OFFER_REASON_NOT_EDITABLE,
    OFFER_REASON_NOT_SENT,
    resolve_offer_action_conflict,
    resolve_offer_pipeline_gate,
)


def test_offer_action_conflicts_follow_state_machine() -> None:
    """Verify pure lifecycle helper returns stable conflict codes by status and action."""
    assert resolve_offer_action_conflict(status="draft", action="edit") is None
    assert resolve_offer_action_conflict(status="draft", action="send") is None
    assert (
        resolve_offer_action_conflict(status="draft", action="accept")
        == OFFER_REASON_NOT_SENT
    )
    assert (
        resolve_offer_action_conflict(status="draft", action="decline")
        == OFFER_REASON_NOT_SENT
    )

    assert (
        resolve_offer_action_conflict(status="sent", action="edit")
        == OFFER_REASON_NOT_EDITABLE
    )
    assert (
        resolve_offer_action_conflict(status="sent", action="send")
        == OFFER_REASON_ALREADY_SENT
    )
    assert resolve_offer_action_conflict(status="sent", action="accept") is None
    assert resolve_offer_action_conflict(status="sent", action="decline") is None

    assert (
        resolve_offer_action_conflict(status="accepted", action="send")
        == OFFER_REASON_ALREADY_ACCEPTED
    )
    assert (
        resolve_offer_action_conflict(status="declined", action="send")
        == OFFER_REASON_ALREADY_DECLINED
    )


def test_offer_pipeline_gate_requires_terminal_offer_state() -> None:
    """Verify pipeline `offer -> hired/rejected` respects accepted and declined statuses."""
    assert resolve_offer_pipeline_gate(status="accepted", to_stage="hired") is None
    assert (
        resolve_offer_pipeline_gate(status="sent", to_stage="hired")
        == OFFER_REASON_NOT_ACCEPTED
    )
    assert (
        resolve_offer_pipeline_gate(status=None, to_stage="hired")
        == OFFER_REASON_NOT_ACCEPTED
    )

    assert resolve_offer_pipeline_gate(status="declined", to_stage="rejected") is None
    assert (
        resolve_offer_pipeline_gate(status="sent", to_stage="rejected")
        == OFFER_REASON_NOT_DECLINED
    )
    assert (
        resolve_offer_pipeline_gate(status=None, to_stage="rejected")
        == OFFER_REASON_NOT_DECLINED
    )
