"""Unit tests for employee directory payload mapping."""

from __future__ import annotations

from datetime import UTC, date, datetime

from hrm_backend.employee.models.avatar import EmployeeProfileAvatar
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.services.employee_directory_service import _to_directory_item


def _build_profile() -> EmployeeProfile:
    """Create in-memory employee profile entity for mapping tests."""
    return EmployeeProfile(
        employee_id="11111111-1111-4111-8111-111111111111",
        hire_conversion_id="22222222-2222-4222-8222-222222222222",
        vacancy_id="33333333-3333-4333-8333-333333333333",
        candidate_id="44444444-4444-4444-8444-444444444444",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+375291234567",
        location="Minsk",
        current_title="Backend Engineer",
        department="Engineering",
        position_title="Platform Engineer",
        manager="Grace Hopper",
        birthday_day_month="03-12",
        is_phone_visible=False,
        is_email_visible=False,
        is_birthday_visible=False,
        is_dismissed=False,
        extra_data_json={"subordinates": 2},
        offer_terms_summary=None,
        start_date=date(2025, 3, 1),
        staff_account_id="staff-1",
        created_by_staff_id="55555555-5555-4555-8555-555555555555",
        created_at=datetime(2026, 3, 1, tzinfo=UTC),
        updated_at=datetime(2026, 3, 1, tzinfo=UTC),
    )


def _build_avatar() -> EmployeeProfileAvatar:
    """Create in-memory avatar metadata entity for mapping tests."""
    return EmployeeProfileAvatar(
        avatar_id="66666666-6666-4666-8666-666666666666",
        employee_id="11111111-1111-4111-8111-111111111111",
        object_key="employees/111/avatar.png",
        mime_type="image/png",
        size_bytes=1234,
        is_active=True,
        updated_at=datetime(2026, 3, 12, tzinfo=UTC),
    )


def test_directory_mapping_shows_private_fields_for_owner() -> None:
    """Verify owner sees phone/email/birthday regardless of privacy flags."""
    profile = _build_profile()
    item = _to_directory_item(
        profile=profile,
        avatar=_build_avatar(),
        actor_subject_id="staff-1",
    )

    assert item.phone == "+375291234567"
    assert item.email == "ada@example.com"
    assert item.birthday_day_month == "03-12"
    assert item.avatar is not None
    assert item.avatar.mime_type == "image/png"


def test_directory_mapping_redacts_private_fields_for_other_viewers() -> None:
    """Verify privacy flags redact optional fields for non-owner viewers."""
    profile = _build_profile()
    item = _to_directory_item(
        profile=profile,
        avatar=None,
        actor_subject_id="staff-2",
    )

    assert item.phone is None
    assert item.email is None
    assert item.birthday_day_month is None
    assert item.avatar is None
