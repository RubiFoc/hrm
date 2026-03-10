"""Pure offer lifecycle helpers shared by pipeline and offer services."""

from __future__ import annotations

from typing import Literal

OfferAction = Literal["edit", "send", "accept", "decline"]

OFFER_REASON_STAGE_NOT_ACTIVE = "offer_stage_not_active"
OFFER_REASON_NOT_FOUND = "offer_not_found"
OFFER_REASON_NOT_EDITABLE = "offer_not_editable"
OFFER_REASON_ALREADY_SENT = "offer_already_sent"
OFFER_REASON_ALREADY_ACCEPTED = "offer_already_accepted"
OFFER_REASON_ALREADY_DECLINED = "offer_already_declined"
OFFER_REASON_NOT_SENT = "offer_not_sent"
OFFER_REASON_TERMS_MISSING = "offer_terms_missing"
OFFER_REASON_NOT_ACCEPTED = "offer_not_accepted"
OFFER_REASON_NOT_DECLINED = "offer_not_declined"


def resolve_offer_action_conflict(*, status: str, action: OfferAction) -> str | None:
    """Return stable reason code when one offer action conflicts with current status."""
    if action == "edit":
        if status == "draft":
            return None
        return OFFER_REASON_NOT_EDITABLE

    if action == "send":
        if status == "draft":
            return None
        if status == "sent":
            return OFFER_REASON_ALREADY_SENT
        if status == "accepted":
            return OFFER_REASON_ALREADY_ACCEPTED
        if status == "declined":
            return OFFER_REASON_ALREADY_DECLINED
        return OFFER_REASON_NOT_EDITABLE

    if action in {"accept", "decline"}:
        if status == "sent":
            return None
        if status == "draft":
            return OFFER_REASON_NOT_SENT
        if status == "accepted":
            return OFFER_REASON_ALREADY_ACCEPTED
        if status == "declined":
            return OFFER_REASON_ALREADY_DECLINED
        return OFFER_REASON_NOT_SENT

    return OFFER_REASON_NOT_EDITABLE


def resolve_offer_pipeline_gate(*, status: str | None, to_stage: str) -> str | None:
    """Return stable blocker for `offer -> hired/rejected` pipeline transitions."""
    if to_stage == "hired":
        if status == "accepted":
            return None
        return OFFER_REASON_NOT_ACCEPTED
    if to_stage == "rejected":
        if status == "declined":
            return None
        return OFFER_REASON_NOT_DECLINED
    return None
