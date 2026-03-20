#!/usr/bin/env python3
"""Select CI execution modes from changed file paths.

The script prints a comma-separated list of modes for the requested job scope:

- ``backend`` -> ``skip``, ``freeze_only``, domain modes, or ``full``
- ``frontend`` -> ``skip``, ``types_only``, contract and domain modes, or ``full``
- ``browser`` -> ``run`` or ``skip``

The GitHub Actions workflow maps the emitted modes to concrete commands.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
    """Selection result for one CI job scope."""

    modes: tuple[str, ...]

    def render(self) -> str:
        """Render the selection as a comma-separated string or ``skip``."""
        return "skip" if not self.modes else ",".join(self.modes)


BACKEND_FULL_PATTERNS = (
    ".github/workflows/**",
    "scripts/ci/**",
    "scripts/check-openapi-freeze.sh",
    "scripts/generate-openapi-frozen.sh",
    "apps/backend/alembic/**",
    "apps/backend/pyproject.toml",
    "apps/backend/uv.lock",
    "apps/backend/src/hrm_backend/api/**",
    "apps/backend/src/hrm_backend/main.py",
    "apps/backend/src/hrm_backend/settings.py",
)
BACKEND_RELEVANT_PATTERNS = (
    "apps/backend/src/hrm_backend/**",
    "apps/backend/tests/**",
)
BACKEND_CORE_PATTERNS = (
    "apps/backend/src/hrm_backend/core/**",
    "apps/backend/tests/unit/core/**",
)
BACKEND_RBAC_PATTERNS = (
    "apps/backend/src/hrm_backend/rbac.py",
    "apps/backend/tests/unit/rbac/**",
)
BACKEND_SECURITY_PATTERNS = (
    "apps/backend/tests/unit/test_cors.py",
    "apps/backend/tests/integration/auth/**",
    "apps/backend/tests/integration/security/**",
)
BACKEND_AUTH_PATTERNS = (
    "apps/backend/src/hrm_backend/auth/**",
    "apps/backend/tests/unit/auth/**",
    "apps/backend/tests/integration/auth/**",
)
BACKEND_ADMIN_PATTERNS = (
    "apps/backend/src/hrm_backend/admin/**",
    "apps/backend/tests/unit/admin/**",
    "apps/backend/tests/integration/admin/**",
)
BACKEND_AUDIT_PATTERNS = (
    "apps/backend/src/hrm_backend/audit/**",
    "apps/backend/tests/unit/audit/**",
    "apps/backend/tests/integration/audit/**",
)
BACKEND_AUTOMATION_PATTERNS = (
    "apps/backend/src/hrm_backend/automation/**",
    "apps/backend/tests/unit/automation/**",
    "apps/backend/tests/integration/automation/**",
    "apps/backend/tests/integration/employee/test_onboarding_task_api.py",
    "apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py",
)
BACKEND_REPORTING_PATTERNS = (
    "apps/backend/src/hrm_backend/reporting/**",
    "apps/backend/tests/unit/reporting/**",
    "apps/backend/tests/integration/reporting/**",
)
BACKEND_CANDIDATE_PATTERNS = (
    "apps/backend/src/hrm_backend/candidates/**",
    "apps/backend/tests/unit/candidates/**",
    "apps/backend/tests/integration/candidates/**",
    "apps/backend/tests/integration/vacancies/test_public_apply_hardening.py",
)
BACKEND_VACANCY_PATTERNS = (
    "apps/backend/src/hrm_backend/vacancies/**",
    "apps/backend/tests/unit/vacancies/**",
    "apps/backend/tests/integration/vacancies/**",
)
BACKEND_INTERVIEW_PATTERNS = (
    "apps/backend/src/hrm_backend/interviews/**",
    "apps/backend/tests/unit/interviews/**",
    "apps/backend/tests/integration/interviews/**",
    "apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py",
)
BACKEND_EMPLOYEE_PATTERNS = (
    "apps/backend/src/hrm_backend/employee/**",
    "apps/backend/tests/unit/employee/**",
    "apps/backend/tests/integration/employee/**",
)
BACKEND_FINANCE_PATTERNS = (
    "apps/backend/src/hrm_backend/finance/**",
    "apps/backend/tests/unit/finance/**",
    "apps/backend/tests/integration/finance/**",
)
BACKEND_NOTIFICATION_PATTERNS = (
    "apps/backend/src/hrm_backend/notifications/**",
    "apps/backend/tests/unit/notifications/**",
    "apps/backend/tests/integration/notifications/**",
)
BACKEND_SCORING_PATTERNS = (
    "apps/backend/src/hrm_backend/scoring/**",
    "apps/backend/tests/unit/scoring/**",
    "apps/backend/tests/integration/scoring/**",
)
BACKEND_PLATFORM_PATTERNS = ("apps/backend/tests/unit/platform/**",)

FRONTEND_FULL_PATTERNS = (
    ".github/workflows/**",
    "scripts/ci/**",
    "apps/frontend/package.json",
    "apps/frontend/src/App.tsx",
    "apps/frontend/src/api/index.ts",
    "apps/frontend/src/app/guards/**",
    "apps/frontend/src/app/router.tsx",
    "apps/frontend/src/main.tsx",
    "apps/frontend/vite.config.*",
)
FRONTEND_RELEVANT_PATTERNS = (
    "apps/frontend/src/**",
)
FRONTEND_CONTRACT_PATTERNS = (
    "apps/frontend/src/api/generated/openapi-types.ts",
    "docs/api/openapi.frozen.json",
)
FRONTEND_ALL_PAGES_PATTERNS = (
    "apps/frontend/src/App.test.tsx",
    "apps/frontend/src/api/auth.ts",
    "apps/frontend/src/api/httpClient.ts",
    "apps/frontend/src/api/typedClient.ts",
    "apps/frontend/src/app/auth/session.ts",
    "apps/frontend/src/app/i18n.ts",
    "apps/frontend/src/app/observability/AppErrorBoundary.*",
    "apps/frontend/src/app/router.*.test.tsx",
    "apps/frontend/src/components/**",
)
FRONTEND_API_PATTERNS = (
    "apps/frontend/src/api/auth.test.ts",
    "apps/frontend/src/api/auth.ts",
    "apps/frontend/src/api/httpClient.test.ts",
    "apps/frontend/src/api/httpClient.ts",
    "apps/frontend/src/api/typedClient.test.ts",
    "apps/frontend/src/api/typedClient.ts",
    "apps/frontend/src/app/auth/session.test.ts",
    "apps/frontend/src/app/auth/session.ts",
)
FRONTEND_LOGIN_PATTERNS = (
    "apps/frontend/src/api/auth.ts",
    "apps/frontend/src/app/auth/session.ts",
    "apps/frontend/src/app/router.auth.test.tsx",
    "apps/frontend/src/pages/LoginPage.*",
)
FRONTEND_CANDIDATE_PATTERNS = (
    "apps/frontend/src/api/candidateAnalysis.ts",
    "apps/frontend/src/api/candidateApplications.ts",
    "apps/frontend/src/api/candidateProfiles.ts",
    "apps/frontend/src/app/candidate/applicationContext.ts",
    "apps/frontend/src/pages/CandidatePage.*",
    "apps/frontend/src/pages/candidate/**",
)
FRONTEND_HR_PATTERNS = (
    "apps/frontend/src/api/candidateAnalysis.ts",
    "apps/frontend/src/api/candidateProfiles.ts",
    "apps/frontend/src/api/interviews.ts",
    "apps/frontend/src/api/matchScores.ts",
    "apps/frontend/src/api/offers.ts",
    "apps/frontend/src/api/vacancies.ts",
    "apps/frontend/src/pages/HrDashboardPage.*",
)
FRONTEND_LEADER_PATTERNS = (
    "apps/frontend/src/api/kpiSnapshots.ts",
    "apps/frontend/src/pages/LeaderWorkspacePage.*",
)
FRONTEND_MANAGER_PATTERNS = (
    "apps/frontend/src/api/managerWorkspace.ts",
    "apps/frontend/src/api/notifications.ts",
    "apps/frontend/src/api/onboardingDashboard.ts",
    "apps/frontend/src/components/NotificationsPanel.*",
    "apps/frontend/src/pages/ManagerWorkspacePage.*",
)
FRONTEND_EMPLOYEE_PATTERNS = (
    "apps/frontend/src/api/employeeOnboarding.ts",
    "apps/frontend/src/app/guards/EmployeeGuard.tsx",
    "apps/frontend/src/app/router.employee.test.tsx",
    "apps/frontend/src/pages/EmployeeOnboardingPage.*",
)
FRONTEND_ACCOUNTANT_PATTERNS = (
    "apps/frontend/src/api/accountingWorkspace.ts",
    "apps/frontend/src/api/notifications.ts",
    "apps/frontend/src/components/NotificationsPanel.*",
    "apps/frontend/src/pages/AccountantWorkspacePage.*",
)
FRONTEND_ADMIN_PATTERNS = (
    "apps/frontend/src/api/adminEmployeeKeys.ts",
    "apps/frontend/src/api/adminStaff.ts",
    "apps/frontend/src/app/guards/AdminGuard.tsx",
    "apps/frontend/src/app/router.admin.test.tsx",
    "apps/frontend/src/pages/AdminEmployeeKeysManagementPage.*",
    "apps/frontend/src/pages/AdminStaffManagementPage.*",
)
FRONTEND_NOTIFICATION_PATTERNS = (
    "apps/frontend/src/api/notifications.ts",
    "apps/frontend/src/components/NotificationsPanel.*",
)
FRONTEND_OBSERVABILITY_PATTERNS = (
    "apps/frontend/src/api/httpClient.test.ts",
    "apps/frontend/src/api/httpClient.ts",
    "apps/frontend/src/app/observability/AppErrorBoundary.*",
    "apps/frontend/src/app/router.observability.test.tsx",
)


def main() -> int:
    """Entry point for change-aware CI scope selection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scope",
        choices=("backend", "frontend", "browser"),
        help="CI scope to evaluate.",
    )
    parser.add_argument(
        "--base-sha",
        default="",
        help="Base commit SHA used to compute the diff.",
    )
    parser.add_argument(
        "--head-sha",
        default="",
        help="Head commit SHA used to compute the diff.",
    )
    args = parser.parse_args()

    changed_files = _changed_files(base_sha=args.base_sha, head_sha=args.head_sha)
    if args.scope == "backend":
        print(_select_backend_modes(changed_files).render())
    elif args.scope == "frontend":
        print(_select_frontend_modes(changed_files).render())
    else:
        print("run" if _should_run_browser_smoke(changed_files) else "skip")
    return 0


def _changed_files(*, base_sha: str, head_sha: str) -> list[str]:
    """Return changed files between two commits.

    The function prefers the merge-base diff so pull requests and push builds both
    resolve to the real changed set instead of a synthetic merge commit view.
    """
    if not base_sha or not head_sha:
        return []

    merge_base = _run_git(["merge-base", base_sha, head_sha])
    diff_base = merge_base or base_sha
    diff_output = _run_git(["diff", "--name-only", f"{diff_base}...{head_sha}"])
    return [line for line in diff_output.splitlines() if line]


def _run_git(args: list[str]) -> str:
    """Run one git command and return stdout as text."""
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _select_backend_modes(changed_files: list[str]) -> Selection:
    """Map backend changes to targeted pytest scopes."""
    if not changed_files:
        return Selection(())

    if _any_match(changed_files, BACKEND_FULL_PATTERNS):
        return Selection(("full",))

    if _any_match(changed_files, ("docs/api/openapi.frozen.json",)) and not _any_match(
        changed_files,
        BACKEND_RELEVANT_PATTERNS,
    ):
        return Selection(("freeze_only",))

    modes: set[str] = set()

    if _any_match(changed_files, BACKEND_CORE_PATTERNS):
        modes.update({"core", "rbac", "security"})

    if _any_match(changed_files, BACKEND_RBAC_PATTERNS):
        modes.update({"rbac", "security"})

    if _any_match(changed_files, BACKEND_SECURITY_PATTERNS):
        modes.add("security")

    if _any_match(changed_files, BACKEND_AUTH_PATTERNS):
        modes.update({"auth", "rbac", "security"})

    if _any_match(changed_files, BACKEND_ADMIN_PATTERNS):
        modes.update({"admin", "rbac", "security"})

    if _any_match(changed_files, BACKEND_AUDIT_PATTERNS):
        modes.add("audit")

    if _any_match(changed_files, BACKEND_AUTOMATION_PATTERNS):
        modes.update({"automation", "reporting"})

    if _any_match(changed_files, BACKEND_REPORTING_PATTERNS):
        modes.add("reporting")

    if _any_match(changed_files, BACKEND_CANDIDATE_PATTERNS):
        modes.add("candidates")

    if _any_match(changed_files, BACKEND_VACANCY_PATTERNS):
        modes.add("vacancies")

    if _any_match(changed_files, BACKEND_INTERVIEW_PATTERNS):
        modes.add("interviews")

    if _any_match(changed_files, BACKEND_EMPLOYEE_PATTERNS):
        modes.add("employee")

    if _any_match(changed_files, BACKEND_FINANCE_PATTERNS):
        modes.add("finance")

    if _any_match(changed_files, BACKEND_NOTIFICATION_PATTERNS):
        modes.add("notifications")

    if _any_match(changed_files, BACKEND_SCORING_PATTERNS):
        modes.add("scoring")

    if _any_match(changed_files, BACKEND_PLATFORM_PATTERNS):
        modes.add("platform")

    if not modes and _any_match(changed_files, BACKEND_RELEVANT_PATTERNS):
        return Selection(("full",))

    ordered = (
        "core",
        "rbac",
        "security",
        "auth",
        "admin",
        "audit",
        "automation",
        "reporting",
        "candidates",
        "vacancies",
        "interviews",
        "employee",
        "finance",
        "notifications",
        "scoring",
        "platform",
    )
    return Selection(tuple(mode for mode in ordered if mode in modes))


def _select_frontend_modes(changed_files: list[str]) -> Selection:
    """Map frontend changes to targeted Vitest scopes."""
    if not changed_files:
        return Selection(())

    if all(
        any(fnmatch.fnmatchcase(path, pattern) for pattern in FRONTEND_CONTRACT_PATTERNS)
        for path in changed_files
    ):
        return Selection(("types_only",))

    if _any_match(changed_files, FRONTEND_FULL_PATTERNS):
        return Selection(("full",))

    contract_changed = _any_match(changed_files, FRONTEND_CONTRACT_PATTERNS)

    modes: set[str] = set()

    if _any_match(changed_files, FRONTEND_ALL_PAGES_PATTERNS):
        modes.add("all_pages")

    if _any_match(changed_files, FRONTEND_API_PATTERNS):
        modes.update({"api", "all_pages"})

    if _any_match(changed_files, FRONTEND_LOGIN_PATTERNS):
        modes.update({"login", "all_pages", "api"})

    if _any_match(changed_files, FRONTEND_CANDIDATE_PATTERNS):
        modes.add("candidate")

    if _any_match(changed_files, FRONTEND_HR_PATTERNS):
        modes.add("hr")

    if _any_match(changed_files, FRONTEND_LEADER_PATTERNS):
        modes.add("leader")

    if _any_match(changed_files, FRONTEND_MANAGER_PATTERNS):
        modes.update({"manager", "notifications"})

    if _any_match(changed_files, FRONTEND_EMPLOYEE_PATTERNS):
        modes.add("employee")

    if _any_match(changed_files, FRONTEND_ACCOUNTANT_PATTERNS):
        modes.update({"accountant", "notifications"})

    if _any_match(changed_files, FRONTEND_ADMIN_PATTERNS):
        modes.add("admin")

    if _any_match(changed_files, FRONTEND_NOTIFICATION_PATTERNS):
        modes.add("notifications")

    if _any_match(changed_files, FRONTEND_OBSERVABILITY_PATTERNS):
        modes.add("observability")

    if contract_changed:
        modes.add("contract")

    if not modes and _any_match(changed_files, FRONTEND_RELEVANT_PATTERNS):
        return Selection(("full",))

    ordered = (
        "types_only",
        "contract",
        "full",
        "all_pages",
        "api",
        "login",
        "candidate",
        "hr",
        "leader",
        "manager",
        "employee",
        "accountant",
        "admin",
        "notifications",
        "observability",
    )
    return Selection(tuple(mode for mode in ordered if mode in modes))


def _should_run_browser_smoke(changed_files: list[str]) -> bool:
    """Return whether browser smoke should run for the changed files."""
    if not changed_files:
        return False

    browser_paths = [
        ".github/workflows/**",
        "apps/backend/alembic/**",
        "apps/backend/src/hrm_backend/admin/**",
        "apps/backend/src/hrm_backend/auth/**",
        "apps/backend/src/hrm_backend/candidates/**",
        "apps/backend/src/hrm_backend/main.py",
        "apps/backend/src/hrm_backend/settings.py",
        "apps/backend/src/hrm_backend/vacancies/**",
        "apps/frontend/src/App.tsx",
        "apps/frontend/src/api/auth.ts",
        "apps/frontend/src/api/candidateAnalysis.ts",
        "apps/frontend/src/api/candidateApplications.ts",
        "apps/frontend/src/api/candidateProfiles.ts",
        "apps/frontend/src/api/httpClient.ts",
        "apps/frontend/src/api/typedClient.ts",
        "apps/frontend/src/app/auth/**",
        "apps/frontend/src/app/guards/**",
        "apps/frontend/src/app/router.admin.test.tsx",
        "apps/frontend/src/app/router.auth.test.tsx",
        "apps/frontend/src/main.tsx",
        "apps/frontend/src/pages/AdminEmployeeKeysManagementPage.*",
        "apps/frontend/src/pages/AdminStaffManagementPage.*",
        "apps/frontend/src/pages/CandidatePage.*",
        "apps/frontend/src/pages/candidate/**",
        "apps/frontend/src/pages/LoginPage.*",
        "docker-compose.yml",
        "docker-compose.*.yml",
        "scripts/browser_auth_smoke.py",
        "scripts/browser_candidate_apply_smoke.py",
        "scripts/browser_candidate_interview_smoke.py",
        "scripts/smoke-compose.sh",
        "scripts/ci/**",
    ]
    return _any_match(changed_files, browser_paths)


def _any_match(paths: list[str], patterns: tuple[str, ...] | list[str]) -> bool:
    """Check whether any path matches any glob pattern."""
    return any(
        fnmatch.fnmatchcase(path, pattern)
        for path in paths
        for pattern in patterns
    )


if __name__ == "__main__":
    raise SystemExit(main())
