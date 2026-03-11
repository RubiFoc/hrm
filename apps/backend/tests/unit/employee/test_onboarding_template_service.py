"""Unit tests for onboarding checklist template payload normalization."""

from __future__ import annotations

import pytest

from hrm_backend.employee.schemas.template import (
    OnboardingChecklistTemplateCreateRequest,
)
from hrm_backend.employee.services.onboarding_template_service import (
    OnboardingTemplateService,
)


class _UnusedSession:
    """Session double used when transaction methods are not exercised."""


class _UnusedDAO:
    """DAO double used when only payload normalization is under test."""


class _UnusedAuditService:
    """Audit double used when no audit writes are expected."""


def _build_service() -> OnboardingTemplateService:
    """Create onboarding template service with inert dependencies for unit tests."""
    return OnboardingTemplateService(
        session=_UnusedSession(),  # type: ignore[arg-type]
        dao=_UnusedDAO(),  # type: ignore[arg-type]
        audit_service=_UnusedAuditService(),  # type: ignore[arg-type]
    )


def test_build_upsert_payload_sorts_and_normalizes_template_items() -> None:
    """Verify template payload builder trims strings and sorts items deterministically."""
    service = _build_service()

    payload = service.build_upsert_payload(
        payload=OnboardingChecklistTemplateCreateRequest(
            name="  Default onboarding  ",
            description="  Core employee ramp-up checklist.  ",
            is_active=True,
            items=[
                {
                    "code": "accounts",
                    "title": " Create accounts ",
                    "description": " Provision required systems ",
                    "sort_order": 20,
                    "is_required": True,
                },
                {
                    "code": "intro",
                    "title": "Team intro",
                    "description": None,
                    "sort_order": 10,
                    "is_required": False,
                },
            ],
        )
    )

    assert payload.name == "Default onboarding"
    assert payload.description == "Core employee ramp-up checklist."
    assert payload.is_active is True
    assert [item.code for item in payload.items] == ["intro", "accounts"]
    assert payload.items[0].title == "Team intro"
    assert payload.items[1].title == "Create accounts"
    assert payload.items[1].description == "Provision required systems"


def test_build_upsert_payload_rejects_duplicate_item_codes() -> None:
    """Verify duplicate template item codes fail closed before persistence."""
    service = _build_service()

    with pytest.raises(ValueError, match="codes must be unique"):
        service.build_upsert_payload(
            payload=OnboardingChecklistTemplateCreateRequest(
                name="Default onboarding",
                description=None,
                is_active=False,
                items=[
                    {
                        "code": "intro",
                        "title": "Team intro",
                        "description": None,
                        "sort_order": 10,
                        "is_required": True,
                    },
                    {
                        "code": "intro",
                        "title": "Second item",
                        "description": None,
                        "sort_order": 20,
                        "is_required": True,
                    },
                ],
            )
        )


def test_build_upsert_payload_rejects_duplicate_sort_orders() -> None:
    """Verify duplicate template item sort orders fail closed before persistence."""
    service = _build_service()

    with pytest.raises(ValueError, match="sort orders must be unique"):
        service.build_upsert_payload(
            payload=OnboardingChecklistTemplateCreateRequest(
                name="Default onboarding",
                description=None,
                is_active=False,
                items=[
                    {
                        "code": "intro",
                        "title": "Team intro",
                        "description": None,
                        "sort_order": 10,
                        "is_required": True,
                    },
                    {
                        "code": "accounts",
                        "title": "Accounts",
                        "description": None,
                        "sort_order": 10,
                        "is_required": True,
                    },
                ],
            )
        )
