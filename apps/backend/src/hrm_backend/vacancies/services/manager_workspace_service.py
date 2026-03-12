"""Read-only manager workspace service for vacancy-scoped hiring visibility.

The service exposes a minimal manager-safe hiring surface on top of the existing recruitment
domain. Visibility is fail-closed and depends only on one persisted ownership signal:
`vacancies.hiring_manager_staff_id == current manager subject`.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.services.candidate_search import build_candidate_list_projection
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.manager_workspace import (
    ManagerWorkspaceCandidateSnapshotItemResponse,
    ManagerWorkspaceCandidateSnapshotResponse,
    ManagerWorkspaceCandidateSnapshotSummaryResponse,
    ManagerWorkspaceHiringSummaryResponse,
    ManagerWorkspaceOverviewResponse,
    ManagerWorkspaceStageSummaryResponse,
    ManagerWorkspaceVacancyListItemResponse,
)
from hrm_backend.vacancies.schemas.pipeline import PipelineStage

MANAGER_WORKSPACE_VACANCY_NOT_FOUND = "manager_workspace_vacancy_not_found"


class ManagerWorkspaceService:
    """Serve read-only hiring visibility for manager workspace requests.

    Inputs:
    - authenticated manager context from the current request;
    - vacancy ownership resolved through `vacancies.hiring_manager_staff_id`;
    - recruitment read models from vacancies, pipeline transitions, candidate profiles/documents,
      and interviews.

    Outputs:
    - overview payload with aggregate hiring counters and manager-visible vacancies;
    - vacancy-scoped candidate snapshot payload for the selected workspace vacancy.

    Side effects:
    - records audit events for successful and denied manager workspace reads.
    - raises `HTTPException(404)` when the requested vacancy is not inside the current manager
      scope.
    """

    def __init__(
        self,
        *,
        vacancy_dao: VacancyDAO,
        transition_dao: PipelineTransitionDAO,
        profile_dao: CandidateProfileDAO,
        document_dao: CandidateDocumentDAO,
        interview_dao: InterviewDAO,
        staff_account_dao: StaffAccountDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize manager workspace service dependencies.

        Args:
            vacancy_dao: Vacancy DAO used to resolve assigned vacancies.
            transition_dao: Pipeline-transition DAO used to build candidate stage snapshots.
            profile_dao: Candidate-profile DAO used to load visible candidate details.
            document_dao: Candidate-document DAO used to expose analysis readiness and parsed CV
                summary data.
            interview_dao: Interview DAO used to expose current interview status for visible
                vacancy-candidate pairs.
            staff_account_dao: Staff-account DAO used to resolve manager login labels.
            audit_service: Audit service used for success/failure evidence.
        """
        self._vacancy_dao = vacancy_dao
        self._transition_dao = transition_dao
        self._profile_dao = profile_dao
        self._document_dao = document_dao
        self._interview_dao = interview_dao
        self._staff_account_dao = staff_account_dao
        self._audit_service = audit_service

    def get_overview(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> ManagerWorkspaceOverviewResponse:
        """Return hiring summary plus manager-visible vacancies.

        Args:
            auth_context: Authenticated manager context.
            request: Active HTTP request used for audit metadata.

        Returns:
            ManagerWorkspaceOverviewResponse: Aggregate counters and assigned vacancies.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        manager_staff_id = str(auth_context.subject_id)
        vacancies = self._vacancy_dao.list_by_hiring_manager_staff_id(manager_staff_id)
        vacancy_ids = [vacancy.vacancy_id for vacancy in vacancies]
        transitions_by_pair = self._transition_dao.get_latest_transitions_for_vacancies(
            vacancy_ids=vacancy_ids,
        )
        interviews = self._interview_dao.list_active_for_vacancies(vacancy_ids=vacancy_ids)
        manager_logins = self._resolve_manager_logins(vacancies)
        now = datetime.now(UTC)

        transitions_by_vacancy: dict[str, list[PipelineTransition]] = defaultdict(list)
        for (vacancy_id, _candidate_id), transition in transitions_by_pair.items():
            transitions_by_vacancy[vacancy_id].append(transition)

        interviews_by_vacancy: dict[str, list[Interview]] = defaultdict(list)
        for interview in interviews:
            interviews_by_vacancy[interview.vacancy_id].append(interview)

        items = [
            _to_manager_workspace_vacancy_item(
                vacancy=vacancy,
                hiring_manager_login=manager_logins.get(vacancy.hiring_manager_staff_id),
                transitions=transitions_by_vacancy.get(vacancy.vacancy_id, []),
                interviews=interviews_by_vacancy.get(vacancy.vacancy_id, []),
            )
            for vacancy in vacancies
        ]
        items.sort(
            key=lambda item: (
                -item.latest_activity_at.timestamp(),
                str(item.vacancy_id),
            ),
        )

        summary = ManagerWorkspaceHiringSummaryResponse(
            vacancy_count=len(vacancies),
            open_vacancy_count=sum(1 for vacancy in vacancies if vacancy.status == "open"),
            candidate_count=len(transitions_by_pair),
            active_interview_count=len(interviews),
            upcoming_interview_count=sum(
                1
                for interview in interviews
                if _normalize_datetime(interview.scheduled_start_at) >= now
            ),
        )
        self._audit_service.record_api_event(
            action="manager_workspace:read",
            resource_type="manager_workspace",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return ManagerWorkspaceOverviewResponse(summary=summary, items=items)

    def get_candidate_snapshot(
        self,
        *,
        vacancy_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> ManagerWorkspaceCandidateSnapshotResponse:
        """Return the visible candidate snapshot for one manager-owned vacancy.

        Args:
            vacancy_id: Vacancy identifier selected in the manager workspace.
            auth_context: Authenticated manager context.
            request: Active HTTP request used for audit metadata.

        Returns:
            ManagerWorkspaceCandidateSnapshotResponse: Vacancy metadata, stage counters, and
                visible candidate rows ordered deterministically by latest stage activity.

        Raises:
            HTTPException: With `404 manager_workspace_vacancy_not_found` when the vacancy is not
                assigned to the current manager.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        manager_staff_id = str(auth_context.subject_id)
        vacancy = self._vacancy_dao.get_by_id(str(vacancy_id))
        if vacancy is None or vacancy.hiring_manager_staff_id != manager_staff_id:
            self._audit_service.record_api_event(
                action="manager_workspace:read",
                resource_type="manager_workspace",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(vacancy_id),
                reason=MANAGER_WORKSPACE_VACANCY_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=MANAGER_WORKSPACE_VACANCY_NOT_FOUND,
            )

        transitions = self._transition_dao.get_latest_transitions_for_vacancy(
            vacancy_id=str(vacancy_id)
        )
        candidate_ids = list(transitions)
        profiles = self._profile_dao.get_by_ids(candidate_ids)
        documents = self._document_dao.get_active_documents_by_candidate_ids(candidate_ids)
        interviews = self._interview_dao.list_active_for_vacancy(vacancy_id=str(vacancy_id))
        interviews_by_candidate = {interview.candidate_id: interview for interview in interviews}
        manager_logins = self._resolve_manager_logins([vacancy])

        items = []
        stage_counter: Counter[PipelineStage] = Counter()
        now = datetime.now(UTC)
        for candidate_id, transition in transitions.items():
            profile = profiles.get(candidate_id)
            if profile is None:
                continue
            projection = build_candidate_list_projection(
                profile=profile,
                active_document=documents.get(candidate_id),
                vacancy_stage=transition.to_stage,  # type: ignore[arg-type]
            )
            interview = interviews_by_candidate.get(candidate_id)
            stage = transition.to_stage  # type: ignore[assignment]
            stage_counter[stage] += 1
            items.append(
                ManagerWorkspaceCandidateSnapshotItemResponse(
                    candidate_id=UUID(profile.candidate_id),
                    first_name=profile.first_name,
                    last_name=profile.last_name,
                    email=profile.email,
                    location=profile.location,
                    current_title=profile.current_title,
                    analysis_ready=projection.analysis_ready,
                    years_experience=projection.years_experience,
                    skills=list(projection.skills),
                    stage=stage,
                    stage_updated_at=_normalize_datetime(transition.transitioned_at),
                    candidate_updated_at=_normalize_datetime(profile.updated_at),
                    interview_status=None if interview is None else interview.status,  # type: ignore[arg-type]
                    interview_scheduled_start_at=(
                        None
                        if interview is None
                        else _normalize_datetime(interview.scheduled_start_at)
                    ),
                    interview_scheduled_end_at=(
                        None
                        if interview is None
                        else _normalize_datetime(interview.scheduled_end_at)
                    ),
                    interview_timezone=None if interview is None else interview.timezone,
                )
            )

        items.sort(
            key=lambda item: (
                -item.stage_updated_at.timestamp(),
                str(item.candidate_id),
            )
        )
        vacancy_item = _to_manager_workspace_vacancy_item(
            vacancy=vacancy,
            hiring_manager_login=manager_logins.get(vacancy.hiring_manager_staff_id),
            transitions=list(transitions.values()),
            interviews=interviews,
        )
        summary = ManagerWorkspaceCandidateSnapshotSummaryResponse(
            candidate_count=len(items),
            active_interview_count=len(interviews),
            upcoming_interview_count=sum(
                1
                for interview in interviews
                if _normalize_datetime(interview.scheduled_start_at) >= now
            ),
            stage_counts=ManagerWorkspaceStageSummaryResponse(
                applied=stage_counter["applied"],
                screening=stage_counter["screening"],
                shortlist=stage_counter["shortlist"],
                interview=stage_counter["interview"],
                offer=stage_counter["offer"],
                hired=stage_counter["hired"],
                rejected=stage_counter["rejected"],
            ),
        )
        self._audit_service.record_api_event(
            action="manager_workspace:read",
            resource_type="manager_workspace",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(vacancy_id),
        )
        return ManagerWorkspaceCandidateSnapshotResponse(
            vacancy=vacancy_item,
            summary=summary,
            items=items,
        )

    def _resolve_manager_logins(self, vacancies: list[Vacancy]) -> dict[str, str]:
        """Resolve manager login labels for the provided vacancies.

        Args:
            vacancies: Vacancy entities that may carry `hiring_manager_staff_id`.

        Returns:
            dict[str, str]: Mapping of `staff_id -> login` for known manager assignments.
        """
        staff_ids = [
            vacancy.hiring_manager_staff_id
            for vacancy in vacancies
            if vacancy.hiring_manager_staff_id is not None
        ]
        accounts = self._staff_account_dao.get_by_ids(staff_ids)
        return {staff_id: account.login for staff_id, account in accounts.items()}


def _to_manager_workspace_vacancy_item(
    *,
    vacancy: Vacancy,
    hiring_manager_login: str | None,
    transitions: list[PipelineTransition],
    interviews: list[Interview],
) -> ManagerWorkspaceVacancyListItemResponse:
    """Map one vacancy plus derived counters to the manager workspace vacancy row schema."""
    activity_candidates = [_normalize_datetime(vacancy.updated_at)]
    activity_candidates.extend(_normalize_datetime(item.transitioned_at) for item in transitions)
    activity_candidates.extend(_normalize_datetime(item.updated_at) for item in interviews)
    latest_activity_at = max(activity_candidates) if activity_candidates else None
    return ManagerWorkspaceVacancyListItemResponse(
        vacancy_id=UUID(vacancy.vacancy_id),
        title=vacancy.title,
        department=vacancy.department,
        status=vacancy.status,
        hiring_manager_staff_id=(
            None
            if vacancy.hiring_manager_staff_id is None
            else UUID(vacancy.hiring_manager_staff_id)
        ),
        hiring_manager_login=hiring_manager_login,
        candidate_count=len(transitions),
        active_interview_count=len(interviews),
        latest_activity_at=latest_activity_at,
        created_at=_normalize_datetime(vacancy.created_at),
        updated_at=_normalize_datetime(vacancy.updated_at),
    )


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize ORM datetimes to timezone-aware UTC values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
