"""Pure helpers for recruiter-facing candidate search, filtering, and list projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.candidates.schemas.parsing import DetectedCVLanguage
from hrm_backend.candidates.schemas.profile import CandidateListItemResponse
from hrm_backend.vacancies.schemas.pipeline import PipelineStage


@dataclass(frozen=True)
class CandidateListFilters:
    """Normalized recruiter-facing candidate list filters.

    Attributes:
        limit: Maximum number of returned rows.
        offset: Number of rows skipped after sorting.
        search: Free-text search query across candidate and parsed CV fields.
        location: Optional case-insensitive location filter.
        current_title: Optional case-insensitive current-title filter.
        skill: Optional case-insensitive skill filter.
        analysis_ready: Optional parsed-analysis readiness filter.
        min_years_experience: Optional minimum total experience threshold.
        vacancy_id: Optional vacancy context used for latest-stage enrichment.
        in_pipeline_only: Whether to keep only candidates that already have vacancy history.
        stage: Optional latest vacancy stage filter.
    """

    limit: int
    offset: int
    search: str | None = None
    location: str | None = None
    current_title: str | None = None
    skill: str | None = None
    analysis_ready: bool | None = None
    min_years_experience: float | None = None
    vacancy_id: UUID | None = None
    in_pipeline_only: bool = False
    stage: PipelineStage | None = None


@dataclass(frozen=True)
class CandidateListProjection:
    """Candidate row enriched with active-CV and vacancy-context fields.

    Attributes:
        profile: Candidate profile entity.
        parsed_profile: Parsed active CV payload when analysis is ready.
        analysis_ready: Whether parsed CV analysis is available for the active document.
        detected_language: Normalized active-document language marker.
        parsed_at: Active-document parsed timestamp when available.
        years_experience: Total parsed experience in years.
        skills: Parsed normalized skills from the active CV.
        vacancy_stage: Latest stage for the requested vacancy, if any.
    """

    profile: CandidateProfile
    parsed_profile: dict[str, object] | None
    analysis_ready: bool
    detected_language: DetectedCVLanguage
    parsed_at: datetime | None
    years_experience: float | None
    skills: tuple[str, ...]
    vacancy_stage: PipelineStage | None


def normalize_candidate_search_value(value: str | None) -> str | None:
    """Normalize one user-provided search/filter fragment for case-insensitive matching.

    Args:
        value: Raw user-provided query fragment.

    Returns:
        str | None: Collapsed, case-folded value or `None` for blank input.
    """
    if value is None:
        return None
    normalized = " ".join(value.split()).casefold()
    return normalized or None


def validate_candidate_list_filters(filters: CandidateListFilters) -> None:
    """Validate cross-field candidate list filter semantics.

    Args:
        filters: Candidate list filter payload.

    Raises:
        HTTPException: If vacancy-scoped filters are used without `vacancy_id`.
    """
    if filters.stage is not None and filters.vacancy_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="stage_requires_vacancy_id",
        )
    if filters.in_pipeline_only and filters.vacancy_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="in_pipeline_only_requires_vacancy_id",
        )


def build_candidate_list_projection(
    *,
    profile: CandidateProfile,
    active_document: CandidateDocument | None,
    vacancy_stage: PipelineStage | None,
) -> CandidateListProjection:
    """Build one candidate list projection from profile, active document, and vacancy context.

    Args:
        profile: Candidate profile row.
        active_document: Active candidate CV row, if any.
        vacancy_stage: Latest vacancy stage for the current list context, if any.

    Returns:
        CandidateListProjection: Enriched candidate list projection for filtering
            and response mapping.
    """
    analysis_ready = bool(
        active_document is not None
        and active_document.parsed_profile_json is not None
        and active_document.parsed_at is not None
    )
    parsed_profile = (
        active_document.parsed_profile_json
        if analysis_ready and isinstance(active_document.parsed_profile_json, dict)
        else None
    )
    return CandidateListProjection(
        profile=profile,
        parsed_profile=parsed_profile,
        analysis_ready=analysis_ready,
        detected_language=_normalize_detected_language(
            None if active_document is None else active_document.detected_language
        ),
        parsed_at=None if active_document is None else active_document.parsed_at,
        years_experience=_extract_years_experience(parsed_profile),
        skills=_extract_skills(parsed_profile),
        vacancy_stage=vacancy_stage,
    )


def matches_candidate_filters(
    projection: CandidateListProjection,
    filters: CandidateListFilters,
) -> bool:
    """Return whether one enriched candidate row satisfies all requested filters.

    Args:
        projection: Enriched candidate row.
        filters: Requested candidate list filters.

    Returns:
        bool: `True` when the row matches all filters.
    """
    if filters.analysis_ready is not None and projection.analysis_ready != filters.analysis_ready:
        return False

    if filters.min_years_experience is not None:
        if (
            projection.years_experience is None
            or projection.years_experience < filters.min_years_experience
        ):
            return False

    if filters.in_pipeline_only and projection.vacancy_stage is None:
        return False

    if filters.stage is not None and projection.vacancy_stage != filters.stage:
        return False

    location_filter = normalize_candidate_search_value(filters.location)
    if location_filter is not None and not _value_matches_filter(
        projection.profile.location,
        location_filter,
    ):
        return False

    current_title_filter = normalize_candidate_search_value(filters.current_title)
    if current_title_filter is not None and not any(
        current_title_filter in candidate_value
        for candidate_value in _current_title_values(projection)
    ):
        return False

    skill_filter = normalize_candidate_search_value(filters.skill)
    if skill_filter is not None and not any(
        skill_filter in skill_value for skill_value in projection.skills
    ):
        return False

    search_filter = normalize_candidate_search_value(filters.search)
    if search_filter is not None and not any(
        search_filter in candidate_value for candidate_value in _search_values(projection)
    ):
        return False

    return True


def sort_candidate_projections(
    projections: list[CandidateListProjection],
) -> list[CandidateListProjection]:
    """Sort candidate list projections by `updated_at desc, candidate_id asc`.

    Args:
        projections: Candidate projections to order.

    Returns:
        list[CandidateListProjection]: Ordered projections.
    """
    ordered_by_id = sorted(projections, key=lambda item: item.profile.candidate_id)
    return sorted(
        ordered_by_id,
        key=lambda item: item.profile.updated_at,
        reverse=True,
    )


def to_candidate_list_item_response(
    projection: CandidateListProjection,
) -> CandidateListItemResponse:
    """Map one enriched candidate projection to the public list response schema.

    Args:
        projection: Enriched candidate projection.

    Returns:
        CandidateListItemResponse: API response payload for one list row.
    """
    return CandidateListItemResponse(
        candidate_id=UUID(projection.profile.candidate_id),
        owner_subject_id=projection.profile.owner_subject_id,
        first_name=projection.profile.first_name,
        last_name=projection.profile.last_name,
        email=projection.profile.email,
        phone=projection.profile.phone,
        location=projection.profile.location,
        current_title=projection.profile.current_title,
        extra_data=projection.profile.extra_data,
        created_at=projection.profile.created_at,
        updated_at=projection.profile.updated_at,
        analysis_ready=projection.analysis_ready,
        detected_language=projection.detected_language,
        parsed_at=projection.parsed_at,
        years_experience=projection.years_experience,
        skills=list(projection.skills),
        vacancy_stage=projection.vacancy_stage,
    )


def _normalize_detected_language(raw_value: str | None) -> DetectedCVLanguage:
    """Normalize stored language markers to the supported API enum values."""
    if raw_value is None:
        return "unknown"
    normalized = raw_value.strip().lower()
    if normalized in {"ru", "en", "mixed", "unknown"}:
        return normalized
    return "unknown"


def _value_matches_filter(candidate_value: str | None, normalized_filter: str) -> bool:
    """Return whether one scalar candidate field matches a normalized filter fragment."""
    normalized_candidate = normalize_candidate_search_value(candidate_value)
    return normalized_candidate is not None and normalized_filter in normalized_candidate


def _search_values(projection: CandidateListProjection) -> tuple[str, ...]:
    """Collect all searchable normalized strings for one candidate projection."""
    values: list[str] = []
    values.extend(
        value
        for value in (
            normalize_candidate_search_value(projection.profile.first_name),
            normalize_candidate_search_value(projection.profile.last_name),
            normalize_candidate_search_value(projection.profile.email),
            normalize_candidate_search_value(projection.profile.phone),
            normalize_candidate_search_value(projection.profile.location),
            normalize_candidate_search_value(projection.profile.current_title),
        )
        if value is not None
    )
    values.extend(_parsed_profile_search_values(projection.parsed_profile))
    return tuple(values)


def _current_title_values(projection: CandidateListProjection) -> tuple[str, ...]:
    """Collect candidate current-title values from profile and parsed active CV."""
    values: list[str] = []
    base_value = normalize_candidate_search_value(projection.profile.current_title)
    if base_value is not None:
        values.append(base_value)

    titles = (
        projection.parsed_profile.get("titles")
        if isinstance(projection.parsed_profile, dict)
        else None
    )
    if not isinstance(titles, dict):
        return tuple(values)

    current = titles.get("current")
    if not isinstance(current, dict):
        return tuple(values)

    for field_name in ("raw", "normalized"):
        normalized = normalize_candidate_search_value(_safe_string(current.get(field_name)))
        if normalized is not None:
            values.append(normalized)
    return tuple(values)


def _parsed_profile_search_values(parsed_profile: dict[str, object] | None) -> tuple[str, ...]:
    """Collect searchable parsed-profile strings required by the list contract."""
    if not isinstance(parsed_profile, dict):
        return ()

    values: list[str] = []
    summary = normalize_candidate_search_value(_safe_string(parsed_profile.get("summary")))
    if summary is not None:
        values.append(summary)

    values.extend(_extract_skills(parsed_profile))
    values.extend(_workplace_search_values(parsed_profile))
    values.extend(_title_search_values(parsed_profile))
    return tuple(values)


def _workplace_search_values(parsed_profile: dict[str, object]) -> tuple[str, ...]:
    """Collect searchable employer and position values from parsed workplaces."""
    workplaces = parsed_profile.get("workplaces")
    if not isinstance(workplaces, dict):
        return ()

    entries = workplaces.get("entries")
    if not isinstance(entries, list):
        return ()

    values: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        employer = normalize_candidate_search_value(_safe_string(entry.get("employer")))
        if employer is not None:
            values.append(employer)

        position = entry.get("position")
        if isinstance(position, dict):
            for field_name in ("raw", "normalized"):
                normalized = normalize_candidate_search_value(
                    _safe_string(position.get(field_name))
                )
                if normalized is not None:
                    values.append(normalized)
    return tuple(values)


def _title_search_values(parsed_profile: dict[str, object]) -> tuple[str, ...]:
    """Collect searchable normalized title values from parsed titles."""
    titles = parsed_profile.get("titles")
    if not isinstance(titles, dict):
        return ()

    values: list[str] = []
    current = titles.get("current")
    if isinstance(current, dict):
        for field_name in ("raw", "normalized"):
            normalized = normalize_candidate_search_value(_safe_string(current.get(field_name)))
            if normalized is not None:
                values.append(normalized)

    past = titles.get("past")
    if isinstance(past, list):
        for item in past:
            if not isinstance(item, dict):
                continue
            for field_name in ("raw", "normalized"):
                normalized = normalize_candidate_search_value(_safe_string(item.get(field_name)))
                if normalized is not None:
                    values.append(normalized)
    return tuple(values)


def _extract_skills(parsed_profile: dict[str, object] | None) -> tuple[str, ...]:
    """Extract normalized parsed skills for matching and list responses."""
    if not isinstance(parsed_profile, dict):
        return ()
    raw_skills = parsed_profile.get("skills")
    if not isinstance(raw_skills, list):
        return ()

    skills: list[str] = []
    for item in raw_skills:
        normalized = normalize_candidate_search_value(_safe_string(item))
        if normalized is not None:
            skills.append(normalized)
    return tuple(skills)


def _extract_years_experience(parsed_profile: dict[str, object] | None) -> float | None:
    """Extract parsed total years of experience from the active CV payload."""
    if not isinstance(parsed_profile, dict):
        return None
    experience = parsed_profile.get("experience")
    if not isinstance(experience, dict):
        return None

    years_total = experience.get("years_total")
    if isinstance(years_total, bool):
        return None
    if isinstance(years_total, (int, float)):
        return float(years_total)
    if isinstance(years_total, str):
        try:
            return float(years_total.strip())
        except ValueError:
            return None
    return None


def _safe_string(value: object) -> str | None:
    """Return a string value when the raw object already contains text."""
    return value if isinstance(value, str) else None
