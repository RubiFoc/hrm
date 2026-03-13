"""Shared notification constants and helper utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

NOTIFICATION_KIND_VACANCY_ASSIGNMENT = "vacancy_assignment"
NOTIFICATION_KIND_ONBOARDING_TASK_ASSIGNMENT = "onboarding_task_assignment"
NOTIFICATION_STATUS_UNREAD = "unread"
NOTIFICATION_STATUS_READ = "read"
DIGEST_UNREAD_LIMIT = 5
NOTIFIABLE_RECIPIENT_ROLES = frozenset({"manager", "accountant"})

NotificationKind = Literal["vacancy_assignment", "onboarding_task_assignment"]
NotificationStatus = Literal["unread", "read"]
NotificationListStatus = Literal["unread", "all"]


def resolve_notification_status(read_at: datetime | None) -> NotificationStatus:
    """Resolve the API notification status from the persisted read timestamp.

    Args:
        read_at: Notification read timestamp if the recipient already acknowledged the item.

    Returns:
        NotificationStatus: `read` when the timestamp exists, otherwise `unread`.
    """
    if read_at is None:
        return NOTIFICATION_STATUS_UNREAD
    return NOTIFICATION_STATUS_READ


def is_notifiable_recipient_role(role: str | None) -> bool:
    """Return whether the provided staff role participates in the v1 notification slice.

    Args:
        role: Staff-account role to evaluate.

    Returns:
        bool: `True` when the role is one of the supported in-app recipient roles.
    """
    return role in NOTIFIABLE_RECIPIENT_ROLES
