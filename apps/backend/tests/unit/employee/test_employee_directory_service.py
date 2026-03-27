"""Unit tests for employee directory mapping and avatar validation helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from io import BytesIO
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.services.employee_directory_service import (
    EMPLOYEE_AVATAR_INVALID_MIME_TYPE,
    EMPLOYEE_AVATAR_TOO_LARGE,
    _compute_tenure_months,
    _to_directory_item,
    _validate_avatar_payload,
)


def test_directory_item_mapping_includes_avatar_and_extra_fields() -> None:
    """Verify directory-card mapper exposes additive profile and avatar fields."""
    entity = EmployeeProfile(
        employee_id="11111111-1111-4111-8111-111111111111",
        hire_conversion_id="22222222-2222-4222-8222-222222222222",
        vacancy_id="33333333-3333-4333-8333-333333333333",
        candidate_id="44444444-4444-4444-8444-444444444444",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+375291234567",
        location="Minsk",
        current_title="Engineer",
        extra_data_json={
            "department": "R&D",
            "manager": "Grace Hopper",
            "subordinates": "3",
            "birthday_day_month": "10-12",
        },
        offer_terms_summary="Base salary 5000 BYN gross.",
        start_date=date(2025, 3, 1),
        staff_account_id=None,
        avatar_object_key="employees/111/avatar/test.jpg",
        avatar_mime_type="image/jpeg",
        avatar_updated_at=datetime(2026, 3, 20, 8, 0, tzinfo=UTC),
        is_dismissed=False,
        created_by_staff_id="55555555-5555-4555-8555-555555555555",
    )

    item = _to_directory_item(entity)

    assert str(item.employee_id) == entity.employee_id
    assert item.full_name == "Ada Lovelace"
    assert item.department == "R&D"
    assert item.manager == "Grace Hopper"
    assert item.subordinates == 3
    assert item.birthday_day_month == "10-12"
    assert item.avatar_url == "/api/v1/employees/11111111-1111-4111-8111-111111111111/avatar"
    assert item.tenure_in_company_months is not None


def test_compute_tenure_months_returns_non_negative_value() -> None:
    """Verify tenure helper never returns negative values for future start dates."""
    future = datetime.now(UTC).date().replace(year=datetime.now(UTC).year + 1)
    assert _compute_tenure_months(future) == 0


@pytest.mark.anyio
async def test_avatar_validation_rejects_unsupported_mime() -> None:
    """Verify avatar validator fails closed for unsupported file MIME type."""
    upload = UploadFile(
        filename="avatar.gif",
        file=BytesIO(b"binary"),
        headers=Headers({"content-type": "image/gif"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await _validate_avatar_payload(file=upload)

    error = exc_info.value
    assert error.detail == EMPLOYEE_AVATAR_INVALID_MIME_TYPE


@pytest.mark.anyio
async def test_avatar_validation_rejects_oversized_payload() -> None:
    """Verify avatar validator rejects payloads above technical reliability limit."""
    oversized = SpooledTemporaryFile(max_size=10 * 1024 * 1024)
    oversized.write(b"x" * (6 * 1024 * 1024))
    oversized.seek(0)
    upload = UploadFile(
        filename="avatar.png",
        file=oversized,
        headers=Headers({"content-type": "image/png"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await _validate_avatar_payload(file=upload)

    error = exc_info.value
    assert error.detail == EMPLOYEE_AVATAR_TOO_LARGE
