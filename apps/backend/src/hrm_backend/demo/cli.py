"""CLI for resetting the database and seeding demo data for local verification.

This module provides a deterministic demo dataset that supports all role-based
workspaces and a minimal recruitment pipeline. It is intended for local/demo
environments only and will truncate all application tables by default.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from hrm_backend.admin.utils.roles import STAFF_ROLES
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.employee.schemas.conversion import (
    HireConversionCandidateSnapshot,
    HireConversionCreate,
    HireConversionOfferSnapshot,
)
from hrm_backend.employee.utils.onboarding import (
    ONBOARDING_RUN_STATUS_STARTED,
    ONBOARDING_TASK_STATUS_PENDING,
)
from hrm_backend.finance.models.salary_band import SalaryBand
from hrm_backend.reporting.models.kpi_snapshot import KpiSnapshot
from hrm_backend.reporting.utils.metrics import KPI_METRIC_KEYS
from hrm_backend.settings import get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy


@dataclass(frozen=True)
class DemoAccount:
    """Credential bundle for one demo staff account.

    Attributes:
        role: Staff role claim used by authorization checks.
        login: Login value used for `/login`.
        email: E-mail address used for authentication and profile matching.
        password: Plaintext demo password (meets policy).
        staff_id: Persisted staff account identifier.
    """

    role: str
    login: str
    email: str
    password: str
    staff_id: str


@dataclass(frozen=True)
class DemoEmployeeKey:
    """One-time employee registration key payload.

    Attributes:
        target_role: Role that can consume the key.
        employee_key: External UUID key value for registration.
        expires_at: Expiration timestamp.
    """

    target_role: str
    employee_key: str
    expires_at: datetime


@dataclass(frozen=True)
class DemoSeedResult:
    """Summary of the demo data created in the database.

    Attributes:
        generated_at: Timestamp when the seed data was generated.
        accounts: Demo staff accounts created for each role.
        employee_keys: One-time registration keys created for non-admin roles.
        vacancy_id: Demo vacancy identifier used across workspaces.
        vacancy_title: Human-readable vacancy title.
        candidate_id: Demo candidate identifier in the HR pipeline.
        employee_candidate_id: Candidate identifier used for employee bootstrap.
        employee_id: Employee profile identifier for the employee workspace.
        onboarding_id: Onboarding run identifier for dashboard and portal views.
    """

    generated_at: datetime
    accounts: list[DemoAccount]
    employee_keys: list[DemoEmployeeKey]
    vacancy_id: str
    vacancy_title: str
    candidate_id: str
    employee_candidate_id: str
    employee_id: str
    onboarding_id: str


@dataclass(frozen=True)
class DemoVacancyCvResult:
    """Summary of a single vacancy and CV document created for verification.

    Attributes:
        generated_at: Timestamp when the vacancy and CV were generated.
        vacancy_id: Newly created vacancy identifier.
        vacancy_title: Human-readable vacancy title.
        candidate_id: Candidate profile identifier linked to the CV.
        candidate_email: Candidate e-mail address.
        document_id: CV document identifier.
        document_filename: Original CV filename.
    """

    generated_at: datetime
    vacancy_id: str
    vacancy_title: str
    candidate_id: str
    candidate_email: str
    document_id: str
    document_filename: str


DEMO_PASSWORD = "DemoPass!1234"
DEMO_ACCOUNTS = (
    ("admin", "admin.demo", "admin.demo@example.com"),
    ("hr", "hr.demo", "hr.demo@example.com"),
    ("manager", "manager.demo", "manager.demo@example.com"),
    ("employee", "employee.demo", "employee.demo@example.com"),
    ("leader", "leader.demo", "leader.demo@example.com"),
    ("accountant", "accountant.demo", "accountant.demo@example.com"),
)


def _resolve_repo_root() -> Path:
    """Resolve repository root by walking parent directories for `AGENTS.md`."""
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if (parent / "AGENTS.md").exists():
            return parent
    return Path.cwd()


def _resolve_output_path(raw: str | None) -> Path:
    """Resolve credentials output path.

    Args:
        raw: Optional path string from CLI.

    Returns:
        Path: Resolved path for credentials output.
    """

    if raw:
        return Path(raw).expanduser().resolve()
    repo_root = _resolve_repo_root()
    return (repo_root / "secrets" / "demo-credentials.txt").resolve()


def _quote_identifier(identifier: str) -> str:
    """Quote a SQL identifier for safe DDL execution."""
    return f"\"{identifier.replace('\"', '\"\"')}\""


def reset_database(database_url: str) -> list[str]:
    """Truncate all application tables except Alembic metadata.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        list[str]: Names of tables that were truncated.

    Raises:
        RuntimeError: If no tables are discovered in the target schema.
    """

    engine = create_engine(database_url, future=True)
    inspector = inspect(engine)
    tables = [
        table
        for table in inspector.get_table_names(schema="public")
        if table != "alembic_version"
    ]
    if not tables:
        raise RuntimeError("No tables found to truncate in the target database")
    quoted = ", ".join(_quote_identifier(table) for table in tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    engine.dispose()
    return tables


def seed_demo_data(database_url: str) -> DemoSeedResult:
    """Insert demo data covering all staff roles and core workflows.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        DemoSeedResult: Summary of created demo data identifiers.
    """

    engine = create_engine(database_url, future=True)
    password_service = PasswordService()
    generated_at = datetime.now(UTC)

    with Session(engine) as session:
        accounts: dict[str, StaffAccount] = {}
        demo_accounts: list[DemoAccount] = []
        for role, login, email in DEMO_ACCOUNTS:
            if role not in STAFF_ROLES:
                raise RuntimeError(f"Unsupported staff role in demo seed: {role}")
            account = StaffAccount(
                login=login,
                email=email,
                password_hash=password_service.hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
                created_at=generated_at,
                updated_at=generated_at,
            )
            session.add(account)
            accounts[role] = account
        session.flush()
        for role, login, email in DEMO_ACCOUNTS:
            account = accounts[role]
            demo_accounts.append(
                DemoAccount(
                    role=role,
                    login=login,
                    email=email,
                    password=DEMO_PASSWORD,
                    staff_id=account.staff_id,
                )
            )

        demo_keys: list[DemoEmployeeKey] = []
        for role in ("hr", "manager", "employee", "leader", "accountant"):
            key_value = str(uuid4())
            expires_at = generated_at + timedelta(days=30)
            session.add(
                EmployeeRegistrationKey(
                    employee_key=key_value,
                    target_role=role,
                    expires_at=expires_at,
                    used_at=None,
                    revoked_at=None,
                    revoked_by_staff_id=None,
                    created_by_staff_id=accounts["admin"].staff_id,
                    created_at=generated_at,
                )
            )
            demo_keys.append(
                DemoEmployeeKey(
                    target_role=role,
                    employee_key=key_value,
                    expires_at=expires_at,
                )
            )

        vacancy = Vacancy(
            title="Warehouse Supervisor",
            description="Lead warehouse operations and coordinate staffing for regional hubs.",
            department="Operations",
            status="open",
            hiring_manager_staff_id=accounts["manager"].staff_id,
            created_at=generated_at,
            updated_at=generated_at,
        )
        session.add(vacancy)
        session.flush()

        session.add(
            SalaryBand(
                vacancy_id=vacancy.vacancy_id,
                band_version=1,
                min_amount=2500,
                max_amount=3500,
                currency="BYN",
                created_by_staff_id=accounts["hr"].staff_id,
                created_at=generated_at,
            )
        )

        candidate = CandidateProfile(
            owner_subject_id="public",
            first_name="Alex",
            last_name="Morgan",
            email="alex.candidate@example.com",
            phone="+375291112233",
            location="Minsk",
            current_title="Operations Analyst",
            extra_data={"source": "demo"},
            created_at=generated_at,
            updated_at=generated_at,
        )
        session.add(candidate)
        session.flush()

        parsed_profile = {
            "summary": "Demo candidate with logistics and operations experience.",
            "skills": ["python", "sql", "logistics"],
            "experience": {"years_total": 5},
            "workplaces": {
                "entries": [
                    {
                        "employer": "Demo Logistics",
                        "position": {"raw": "Analyst", "normalized": "analyst"},
                    }
                ]
            },
            "titles": {
                "current": {"raw": "Operations Analyst", "normalized": "operations analyst"},
                "past": [],
            },
        }
        evidence = [
            {"field": "skills", "snippet": "Python, SQL, logistics"},
            {"field": "workplaces", "snippet": "Demo Logistics"},
        ]
        session.add(
            CandidateDocument(
                candidate_id=candidate.candidate_id,
                object_key=f"candidates/{candidate.candidate_id}/cv/{uuid4()}.pdf",
                filename="alex_morgan_cv.pdf",
                mime_type="application/pdf",
                size_bytes=2048,
                checksum_sha256=hashlib.sha256(candidate.candidate_id.encode("utf-8")).hexdigest(),
                is_active=True,
                parsed_profile_json=parsed_profile,
                evidence_json=evidence,
                detected_language="en",
                parsed_at=generated_at,
                created_at=generated_at,
            )
        )

        transitions = [
            PipelineTransition(
                transition_id=str(uuid4()),
                vacancy_id=vacancy.vacancy_id,
                candidate_id=candidate.candidate_id,
                from_stage=None,
                to_stage="applied",
                reason="demo_seed",
                changed_by_sub=accounts["hr"].staff_id,
                changed_by_role="hr",
                transitioned_at=generated_at - timedelta(days=3),
            ),
            PipelineTransition(
                transition_id=str(uuid4()),
                vacancy_id=vacancy.vacancy_id,
                candidate_id=candidate.candidate_id,
                from_stage="applied",
                to_stage="screening",
                reason="demo_seed",
                changed_by_sub=accounts["hr"].staff_id,
                changed_by_role="hr",
                transitioned_at=generated_at - timedelta(days=2),
            ),
            PipelineTransition(
                transition_id=str(uuid4()),
                vacancy_id=vacancy.vacancy_id,
                candidate_id=candidate.candidate_id,
                from_stage="screening",
                to_stage="shortlist",
                reason="demo_seed",
                changed_by_sub=accounts["hr"].staff_id,
                changed_by_role="hr",
                transitioned_at=generated_at - timedelta(days=1),
            ),
        ]
        session.add_all(transitions)

        employee_candidate = CandidateProfile(
            owner_subject_id="public",
            first_name="Taylor",
            last_name="Employee",
            email=accounts["employee"].email,
            phone="+375291998877",
            location="Minsk",
            current_title="Assistant",
            extra_data={"source": "demo"},
            created_at=generated_at,
            updated_at=generated_at,
        )
        session.add(employee_candidate)
        session.flush()

        session.add(
            CandidateDocument(
                candidate_id=employee_candidate.candidate_id,
                object_key=f"candidates/{employee_candidate.candidate_id}/cv/{uuid4()}.pdf",
                filename="taylor_employee_cv.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                checksum_sha256=hashlib.sha256(
                    employee_candidate.candidate_id.encode("utf-8")
                ).hexdigest(),
                is_active=True,
                parsed_profile_json={
                    "summary": "Demo hire conversion candidate.",
                    "skills": ["operations"],
                    "experience": {"years_total": 2},
                    "workplaces": {"entries": []},
                    "titles": {
                        "current": {"raw": "Assistant", "normalized": "assistant"},
                        "past": [],
                    },
                },
                evidence_json=[{"field": "skills", "snippet": "operations"}],
                detected_language="en",
                parsed_at=generated_at,
                created_at=generated_at,
            )
        )

        offer_transition_id = str(uuid4())
        hired_transition_id = str(uuid4())
        session.add_all(
            [
                PipelineTransition(
                    transition_id=str(uuid4()),
                    vacancy_id=vacancy.vacancy_id,
                    candidate_id=employee_candidate.candidate_id,
                    from_stage=None,
                    to_stage="applied",
                    reason="demo_seed",
                    changed_by_sub=accounts["hr"].staff_id,
                    changed_by_role="hr",
                    transitioned_at=generated_at - timedelta(days=7),
                ),
                PipelineTransition(
                    transition_id=str(uuid4()),
                    vacancy_id=vacancy.vacancy_id,
                    candidate_id=employee_candidate.candidate_id,
                    from_stage="applied",
                    to_stage="interview",
                    reason="demo_seed",
                    changed_by_sub=accounts["hr"].staff_id,
                    changed_by_role="hr",
                    transitioned_at=generated_at - timedelta(days=6),
                ),
                PipelineTransition(
                    transition_id=offer_transition_id,
                    vacancy_id=vacancy.vacancy_id,
                    candidate_id=employee_candidate.candidate_id,
                    from_stage="interview",
                    to_stage="offer",
                    reason="demo_seed",
                    changed_by_sub=accounts["hr"].staff_id,
                    changed_by_role="hr",
                    transitioned_at=generated_at - timedelta(days=5),
                ),
                PipelineTransition(
                    transition_id=hired_transition_id,
                    vacancy_id=vacancy.vacancy_id,
                    candidate_id=employee_candidate.candidate_id,
                    from_stage="offer",
                    to_stage="hired",
                    reason="demo_seed",
                    changed_by_sub=accounts["hr"].staff_id,
                    changed_by_role="hr",
                    transitioned_at=generated_at - timedelta(days=4),
                ),
            ]
        )

        offer = Offer(
            vacancy_id=vacancy.vacancy_id,
            candidate_id=employee_candidate.candidate_id,
            status="accepted",
            terms_summary="Base salary 3000 BYN",
            proposed_start_date=date.today() + timedelta(days=14),
            expires_at=date.today() + timedelta(days=30),
            note="Demo offer",
            sent_at=generated_at - timedelta(days=5),
            sent_by_staff_id=accounts["hr"].staff_id,
            decision_at=generated_at - timedelta(days=4),
            decision_note="Accepted for demo.",
            decision_recorded_by_staff_id=accounts["hr"].staff_id,
            created_at=generated_at - timedelta(days=5),
            updated_at=generated_at - timedelta(days=4),
        )
        session.add(offer)
        session.flush()

        conversion_payload = HireConversionCreate(
            vacancy_id=UUID(vacancy.vacancy_id),
            candidate_id=UUID(employee_candidate.candidate_id),
            offer_id=UUID(offer.offer_id),
            hired_transition_id=UUID(hired_transition_id),
            candidate_snapshot=HireConversionCandidateSnapshot(
                first_name=employee_candidate.first_name,
                last_name=employee_candidate.last_name,
                email=employee_candidate.email,
                phone=employee_candidate.phone,
                location=employee_candidate.location,
                current_title=employee_candidate.current_title,
                extra_data=dict(employee_candidate.extra_data or {}),
            ),
            offer_snapshot=HireConversionOfferSnapshot(
                status="accepted",
                terms_summary=offer.terms_summary,
                proposed_start_date=offer.proposed_start_date,
                expires_at=offer.expires_at,
                note=offer.note,
                sent_at=offer.sent_at,
                sent_by_staff_id=UUID(offer.sent_by_staff_id),
                decision_at=offer.decision_at,
                decision_note=offer.decision_note,
                decision_recorded_by_staff_id=UUID(offer.decision_recorded_by_staff_id),
            ),
            converted_by_staff_id=UUID(accounts["hr"].staff_id),
        )

        conversion = HireConversion(
            vacancy_id=str(conversion_payload.vacancy_id),
            candidate_id=str(conversion_payload.candidate_id),
            offer_id=str(conversion_payload.offer_id),
            hired_transition_id=str(conversion_payload.hired_transition_id),
            status=conversion_payload.status,
            candidate_snapshot_json=conversion_payload.candidate_snapshot.model_dump(mode="json"),
            offer_snapshot_json=conversion_payload.offer_snapshot.model_dump(mode="json"),
            converted_by_staff_id=str(conversion_payload.converted_by_staff_id),
            converted_at=generated_at - timedelta(days=4),
        )
        session.add(conversion)
        session.flush()

        template = OnboardingTemplate(
            name="Demo onboarding",
            description="Seeded demo onboarding checklist.",
            is_active=True,
            created_by_staff_id=accounts["hr"].staff_id,
            created_at=generated_at - timedelta(days=4),
            updated_at=generated_at - timedelta(days=4),
        )
        session.add(template)
        session.flush()

        template_items = [
            OnboardingTemplateItem(
                template_id=template.template_id,
                code="profile_complete",
                title="Complete employee profile",
                description="Provide missing profile information.",
                sort_order=1,
                is_required=True,
            ),
            OnboardingTemplateItem(
                template_id=template.template_id,
                code="manager_intro",
                title="Manager introduction",
                description="Manager welcome and first-week plan.",
                sort_order=2,
                is_required=True,
            ),
            OnboardingTemplateItem(
                template_id=template.template_id,
                code="accounting_setup",
                title="Accounting onboarding",
                description="Submit payroll onboarding details.",
                sort_order=3,
                is_required=True,
            ),
        ]
        session.add_all(template_items)

        employee_profile = EmployeeProfile(
            hire_conversion_id=conversion.conversion_id,
            vacancy_id=vacancy.vacancy_id,
            candidate_id=employee_candidate.candidate_id,
            first_name=employee_candidate.first_name,
            last_name=employee_candidate.last_name,
            email=employee_candidate.email,
            phone=employee_candidate.phone,
            location=employee_candidate.location,
            current_title=employee_candidate.current_title,
            department="Operations",
            position_title="Operations Assistant",
            manager="Morgan Manager",
            birthday_day_month="05-12",
            is_phone_visible=True,
            is_email_visible=True,
            is_birthday_visible=False,
            is_dismissed=False,
            extra_data_json={"source": "demo"},
            offer_terms_summary=offer.terms_summary,
            start_date=offer.proposed_start_date,
            staff_account_id=accounts["employee"].staff_id,
            created_by_staff_id=accounts["hr"].staff_id,
            created_at=generated_at - timedelta(days=4),
            updated_at=generated_at - timedelta(days=4),
        )
        session.add(employee_profile)
        session.flush()

        onboarding_run = OnboardingRun(
            employee_id=employee_profile.employee_id,
            hire_conversion_id=conversion.conversion_id,
            status=ONBOARDING_RUN_STATUS_STARTED,
            started_at=generated_at - timedelta(days=4),
            started_by_staff_id=accounts["hr"].staff_id,
        )
        session.add(onboarding_run)
        session.flush()

        task_map = {
            "profile_complete": ("employee", accounts["employee"].staff_id),
            "manager_intro": ("manager", accounts["manager"].staff_id),
            "accounting_setup": ("accountant", accounts["accountant"].staff_id),
        }
        onboarding_tasks: list[OnboardingTask] = []
        for item in template_items:
            role, staff_id = task_map[item.code]
            onboarding_tasks.append(
                OnboardingTask(
                    onboarding_id=onboarding_run.onboarding_id,
                    template_id=template.template_id,
                    template_item_id=item.template_item_id,
                    code=item.code,
                    title=item.title,
                    description=item.description,
                    sort_order=item.sort_order,
                    is_required=item.is_required,
                    status=ONBOARDING_TASK_STATUS_PENDING,
                    assigned_role=role,
                    assigned_staff_id=staff_id,
                    due_at=generated_at + timedelta(days=14),
                    created_at=generated_at - timedelta(days=4),
                    updated_at=generated_at - timedelta(days=4),
                )
            )
        session.add_all(onboarding_tasks)

        period_month = date.today().replace(day=1)
        metric_values = {
            "vacancies_created_count": 1,
            "candidates_applied_count": 2,
            "interviews_scheduled_count": 1,
            "offers_sent_count": 1,
            "offers_accepted_count": 1,
            "hires_count": 1,
            "onboarding_started_count": 1,
            "onboarding_tasks_completed_count": 0,
            "total_hr_operations_count": 10,
            "automated_hr_operations_count": 4,
            "automated_hr_operations_share_percent": 40,
        }
        for metric_key in KPI_METRIC_KEYS:
            session.add(
                KpiSnapshot(
                    period_month=period_month,
                    metric_key=metric_key,
                    metric_value=metric_values.get(metric_key, 0),
                    generated_at=generated_at,
                )
            )

        session.commit()

        result = DemoSeedResult(
            generated_at=generated_at,
            accounts=demo_accounts,
            employee_keys=demo_keys,
            vacancy_id=vacancy.vacancy_id,
            vacancy_title=vacancy.title,
            candidate_id=candidate.candidate_id,
            employee_candidate_id=employee_candidate.candidate_id,
            employee_id=employee_profile.employee_id,
            onboarding_id=onboarding_run.onboarding_id,
        )

    engine.dispose()
    return result


def _select_staff_by_role(session: Session, role: str) -> StaffAccount | None:
    """Return the first staff account for a given role, if present.

    Args:
        session: Active SQLAlchemy session.
        role: Staff role to filter by.

    Returns:
        StaffAccount | None: Matching staff account, if any.
    """

    return session.query(StaffAccount).filter(StaffAccount.role == role).first()


def create_demo_vacancy_with_cv(database_url: str) -> DemoVacancyCvResult:
    """Create one vacancy and one candidate CV for quick verification.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        DemoVacancyCvResult: Summary of created vacancy and CV identifiers.

    Raises:
        RuntimeError: If no staff accounts exist to own the records.

    Side Effects:
        Inserts a vacancy, salary band, candidate profile, candidate document, and pipeline
        transition.
    """

    engine = create_engine(database_url, future=True)
    generated_at = datetime.now(UTC)

    with Session(engine) as session:
        hr_account = _select_staff_by_role(session, "hr")
        manager_account = _select_staff_by_role(session, "manager")
        fallback_account = hr_account or manager_account or session.query(StaffAccount).first()

        if fallback_account is None:
            raise RuntimeError(
                "No staff accounts found; seed demo accounts before creating vacancy"
            )

        created_by_staff_id = (hr_account or fallback_account).staff_id
        hiring_manager_staff_id = (manager_account or fallback_account).staff_id
        changed_by_role = (hr_account or fallback_account).role

        unique_suffix = generated_at.strftime("%Y%m%d%H%M%S")
        vacancy_title = f"Demo Warehouse Coordinator {unique_suffix}"
        vacancy = Vacancy(
            title=vacancy_title,
            description="Coordinate inbound inventory and shift schedules for demo verification.",
            department="Operations",
            status="open",
            hiring_manager_staff_id=hiring_manager_staff_id,
            created_at=generated_at,
            updated_at=generated_at,
        )
        session.add(vacancy)
        session.flush()

        session.add(
            SalaryBand(
                vacancy_id=vacancy.vacancy_id,
                band_version=1,
                min_amount=2200,
                max_amount=3200,
                currency="BYN",
                created_by_staff_id=created_by_staff_id,
                created_at=generated_at,
            )
        )

        candidate_email = f"demo.candidate.{uuid4().hex[:8]}@example.com"
        candidate = CandidateProfile(
            owner_subject_id="public",
            first_name="Casey",
            last_name="Rivera",
            email=candidate_email,
            phone="+375291234567",
            location="Minsk",
            current_title="Warehouse Specialist",
            extra_data={"source": "demo_vacancy_cv"},
            created_at=generated_at,
            updated_at=generated_at,
        )
        session.add(candidate)
        session.flush()

        document = CandidateDocument(
            candidate_id=candidate.candidate_id,
            object_key=f"candidates/{candidate.candidate_id}/cv/{uuid4()}.pdf",
            filename="casey_rivera_cv.pdf",
            mime_type="application/pdf",
            size_bytes=3072,
            checksum_sha256=hashlib.sha256(candidate.candidate_id.encode("utf-8")).hexdigest(),
            is_active=True,
            parsed_profile_json={
                "summary": "Demo CV for warehouse coordination.",
                "skills": ["inventory", "shift_planning", "excel"],
                "experience": {"years_total": 4},
                "workplaces": {
                    "entries": [
                        {
                            "employer": "Demo Warehouse",
                            "position": {"raw": "Specialist"},
                        }
                    ]
                },
                "titles": {
                    "current": {
                        "raw": "Warehouse Specialist",
                        "normalized": "warehouse specialist",
                    }
                },
            },
            evidence_json=[{"field": "skills", "snippet": "Inventory, shift planning, Excel"}],
            detected_language="en",
            parsed_at=generated_at,
            created_at=generated_at,
        )
        session.add(document)
        session.flush()

        session.add(
            PipelineTransition(
                transition_id=str(uuid4()),
                vacancy_id=vacancy.vacancy_id,
                candidate_id=candidate.candidate_id,
                from_stage=None,
                to_stage="applied",
                reason="demo_vacancy_cv",
                changed_by_sub=created_by_staff_id,
                changed_by_role=changed_by_role,
                transitioned_at=generated_at,
            )
        )

        session.commit()

        result = DemoVacancyCvResult(
            generated_at=generated_at,
            vacancy_id=vacancy.vacancy_id,
            vacancy_title=vacancy.title,
            candidate_id=candidate.candidate_id,
            candidate_email=candidate.email,
            document_id=document.document_id,
            document_filename=document.filename,
        )

    engine.dispose()
    return result


def write_credentials_file(result: DemoSeedResult, output_path: Path) -> None:
    """Write demo credentials and key identifiers to a text file.

    Args:
        result: Summary of demo seed output.
        output_path: Target file path for credentials.

    Side Effects:
        Creates parent directories and writes a plaintext credentials file.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "HRM Demo Credentials",
        f"Generated at: {result.generated_at.isoformat()}",
        "",
        "Staff accounts:",
    ]
    for account in result.accounts:
        lines.append(
            f"- role={account.role} login={account.login} email={account.email} "
            f"password={account.password}"
        )
    lines.extend(
        [
            "",
            "Employee registration keys:",
        ]
    )
    for key in result.employee_keys:
        lines.append(
            f"- target_role={key.target_role} key={key.employee_key} "
            f"expires_at={key.expires_at.isoformat()}"
        )
    lines.extend(
        [
            "",
            "Demo entities:",
            f"- vacancy_id={result.vacancy_id}",
            f"- vacancy_title={result.vacancy_title}",
            f"- candidate_id={result.candidate_id}",
            f"- employee_candidate_id={result.employee_candidate_id}",
            f"- employee_id={result.employee_id}",
            f"- onboarding_id={result.onboarding_id}",
            "",
            "Notes:",
            "- Candidate access is public via /careers and /candidate/apply.",
            "- Staff logins use /login with the accounts above.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_vacancy_cv_to_file(result: DemoVacancyCvResult, output_path: Path) -> None:
    """Append a vacancy + CV summary to an existing credentials file.

    Args:
        result: Summary of the created vacancy and CV.
        output_path: Target file path for credentials.

    Side Effects:
        Creates parent directories if needed and appends to the credentials file.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        needs_newline = not existing.endswith("\n")
    else:
        output_path.write_text("HRM Demo Credentials\n", encoding="utf-8")
        needs_newline = True

    lines = [
        "Additional demo vacancy + CV:",
        f"Generated at: {result.generated_at.isoformat()}",
        f"- vacancy_id={result.vacancy_id}",
        f"- vacancy_title={result.vacancy_title}",
        f"- candidate_id={result.candidate_id}",
        f"- candidate_email={result.candidate_email}",
        f"- document_id={result.document_id}",
        f"- document_filename={result.document_filename}",
    ]
    with output_path.open("a", encoding="utf-8") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for demo seeding.

    Returns:
        argparse.Namespace: Parsed argument bundle.
    """

    parser = argparse.ArgumentParser(
        description="Reset database and seed demo data for HRM local verification.",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="Override database URL (defaults to settings).",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="Credentials output path (default: secrets/demo-credentials.txt).",
    )
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Skip truncating the database before seeding.",
    )
    parser.add_argument(
        "--create-vacancy-cv",
        action="store_true",
        help="Create one vacancy and CV without resetting or seeding full demo data.",
    )
    return parser.parse_args()


def main() -> None:
    """Execute demo database reset + seed workflow.

    Side Effects:
        - Truncates all application tables (unless skipped).
        - Inserts demo data across staff, recruitment, onboarding, and reporting domains.
        - Writes plaintext credentials file for local verification.
    """

    args = parse_args()
    settings = get_settings()
    database_url = args.database_url or settings.database_url
    output_path = _resolve_output_path(args.output_path)

    if args.create_vacancy_cv:
        result = create_demo_vacancy_with_cv(database_url)
        append_vacancy_cv_to_file(result, output_path)
        print(f"Demo vacancy + CV created. Details appended to: {output_path}")
        return

    if not args.skip_reset:
        reset_database(database_url)

    result = seed_demo_data(database_url)
    write_credentials_file(result, output_path)

    print(f"Demo seed complete. Credentials written to: {output_path}")


if __name__ == "__main__":
    main()
