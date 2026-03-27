"""Referral API schemas."""

from hrm_backend.referrals.schemas.referral import (
    ReferralCreate,
    ReferralListItemResponse,
    ReferralListResponse,
    ReferralReviewRequest,
    ReferralReviewResponse,
    ReferralSubmitResponse,
)

__all__ = [
    "ReferralCreate",
    "ReferralSubmitResponse",
    "ReferralListItemResponse",
    "ReferralListResponse",
    "ReferralReviewRequest",
    "ReferralReviewResponse",
]
