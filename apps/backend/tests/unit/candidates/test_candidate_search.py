"""Unit tests for recruiter-facing candidate list search and filter helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.candidates.services.candidate_search import (
    CandidateListFilters,
    build_candidate_list_projection,
    matches_candidate_filters,
    normalize_candidate_search_value,
    validate_candidate_list_filters,
)

NOW = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)


def test_normalize_candidate_search_value_collapses_whitespace_and_case() -> None:
    """Verify free-text matching uses stable case-insensitive normalized fragments."""
    assert normalize_candidate_search_value("  Senior   PYTHON  ") == "senior python"
    assert normalize_candidate_search_value("   ") is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("acme logistics", True),
        ("warehouse supervisor", True),
        ("logistics lead", True),
        ("python", True),
        ("not-present", False),
    ],
)
def test_matches_candidate_filters_searches_profile_and_parsed_cv_fields(
    query: str,
    expected: bool,
) -> None:
    """Verify free-text search spans base profile fields plus parsed CV enrichment fields."""
    projection = _build_projection()

    assert (
        matches_candidate_filters(
            projection,
            CandidateListFilters(limit=20, offset=0, search=query),
        )
        is expected
    )


def test_matches_candidate_filters_supports_skill_contains_matching() -> None:
    """Verify skill filter matches parsed skills with case-insensitive contains semantics."""
    projection = _build_projection()

    assert matches_candidate_filters(
        projection,
        CandidateListFilters(limit=20, offset=0, skill="machine"),
    )
    assert not matches_candidate_filters(
        projection,
        CandidateListFilters(limit=20, offset=0, skill="react"),
    )


def test_matches_candidate_filters_distinguishes_analysis_ready_states() -> None:
    """Verify analysis-ready filter requires both parsed payload and parsed timestamp."""
    ready_projection = _build_projection()
    pending_projection = _build_projection(parsed_at=None)

    assert matches_candidate_filters(
        ready_projection,
        CandidateListFilters(limit=20, offset=0, analysis_ready=True),
    )
    assert not matches_candidate_filters(
        pending_projection,
        CandidateListFilters(limit=20, offset=0, analysis_ready=True),
    )
    assert matches_candidate_filters(
        pending_projection,
        CandidateListFilters(limit=20, offset=0, analysis_ready=False),
    )


def test_matches_candidate_filters_applies_min_years_experience_only_when_present() -> None:
    """Verify minimum experience excludes rows without parsed totals and rows below threshold."""
    experienced_projection = _build_projection(years_total=5)
    missing_experience_projection = _build_projection(
        parsed_profile={"summary": "No years extracted."},
    )

    assert matches_candidate_filters(
        experienced_projection,
        CandidateListFilters(limit=20, offset=0, min_years_experience=4),
    )
    assert not matches_candidate_filters(
        experienced_projection,
        CandidateListFilters(limit=20, offset=0, min_years_experience=6),
    )
    assert not matches_candidate_filters(
        missing_experience_projection,
        CandidateListFilters(limit=20, offset=0, min_years_experience=1),
    )


def test_matches_candidate_filters_applies_vacancy_stage_filters() -> None:
    """Verify vacancy-scoped filters use the latest resolved stage from the requested vacancy."""
    projection = _build_projection(vacancy_stage="interview")
    filters = CandidateListFilters(
        limit=20,
        offset=0,
        vacancy_id=uuid4(),
        in_pipeline_only=True,
        stage="interview",
    )

    assert matches_candidate_filters(projection, filters)
    assert not matches_candidate_filters(
        projection,
        CandidateListFilters(
            limit=20,
            offset=0,
            vacancy_id=uuid4(),
            in_pipeline_only=True,
            stage="offer",
        ),
    )
    assert not matches_candidate_filters(
        _build_projection(vacancy_stage=None),
        CandidateListFilters(limit=20, offset=0, vacancy_id=uuid4(), in_pipeline_only=True),
    )


def test_validate_candidate_list_filters_rejects_stage_without_vacancy() -> None:
    """Verify `stage` cannot be used without a vacancy-scoped context."""
    with pytest.raises(HTTPException) as error_info:
        validate_candidate_list_filters(
            CandidateListFilters(limit=20, offset=0, stage="screening"),
        )

    assert error_info.value.status_code == 422
    assert error_info.value.detail == "stage_requires_vacancy_id"


def _build_projection(
    *,
    parsed_profile: dict[str, object] | None = None,
    parsed_at: datetime | None = NOW,
    years_total: int | None = 5,
    vacancy_stage: str | None = "screening",
):
    """Build one enriched candidate projection for pure helper tests."""
    candidate_id = str(uuid4())
    profile = CandidateProfile(
        candidate_id=candidate_id,
        owner_subject_id="public",
        first_name="Alice",
        last_name="Johnson",
        email="alice@example.com",
        phone="+375291112233",
        location="Minsk",
        current_title="Recruiter",
        extra_data={},
        created_at=NOW,
        updated_at=NOW,
    )
    document = CandidateDocument(
        document_id=str(uuid4()),
        candidate_id=candidate_id,
        object_key="candidates/test/cv.pdf",
        filename="cv.pdf",
        mime_type="application/pdf",
        size_bytes=123,
        checksum_sha256="0" * 64,
        is_active=True,
        parsed_profile_json=parsed_profile
        or {
            "summary": "Experienced logistics lead with strong warehouse hiring support.",
            "skills": ["python", "machine_learning"],
            "experience": {"years_total": years_total},
            "workplaces": {
                "entries": [
                    {
                        "employer": "Acme Logistics",
                        "position": {
                            "raw": "Warehouse Supervisor",
                            "normalized": "warehouse supervisor",
                        },
                    }
                ]
            },
            "titles": {
                "current": {
                    "raw": "Logistics Lead",
                    "normalized": "logistics lead",
                },
                "past": [],
            },
        },
        detected_language="en",
        parsed_at=parsed_at,
        created_at=NOW,
    )
    return build_candidate_list_projection(
        profile=profile,
        active_document=document,
        vacancy_stage=vacancy_stage,  # type: ignore[arg-type]
    )
