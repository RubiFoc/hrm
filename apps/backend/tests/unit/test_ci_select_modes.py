"""Regression tests for the change-aware CI selector.

The GitHub Actions workflow depends on this helper to decide when to skip jobs
and when to narrow test targets. These tests keep the path-to-mode mapping
stable for the most important slices.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SELECTOR_PATH = REPO_ROOT / "scripts" / "ci" / "select_ci_modes.py"


def _load_selector_module():
    """Load the CI selector script as a Python module."""
    spec = spec_from_file_location("ci_select_ci_modes", SELECTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load selector module from {SELECTOR_PATH}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_backend_automation_changes_select_reporting_and_automation() -> None:
    """Automation executor changes should pull automation and reporting coverage."""
    selector = _load_selector_module()

    selection = selector._select_backend_modes(
        [
            "apps/backend/src/hrm_backend/automation/services/executor.py",
            "apps/backend/src/hrm_backend/reporting/services/kpi_snapshot_service.py",
        ]
    )

    assert selection.render() == "automation,reporting"


def test_backend_openapi_only_changes_select_freeze_only() -> None:
    """Frozen OpenAPI drift alone should run the freeze check only."""
    selector = _load_selector_module()

    selection = selector._select_backend_modes(["docs/api/openapi.frozen.json"])

    assert selection.render() == "freeze_only"


def test_backend_workflow_changes_force_full_suite() -> None:
    """CI workflow edits should keep the backend job on the safe full path."""
    selector = _load_selector_module()

    selection = selector._select_backend_modes([".github/workflows/ci.yml"])

    assert selection.render() == "full"


def test_frontend_session_changes_select_shared_routes_and_api_tests() -> None:
    """Auth session changes should run shared route tests and API client coverage."""
    selector = _load_selector_module()

    selection = selector._select_frontend_modes(
        [
            "apps/frontend/src/app/auth/session.ts",
            "apps/frontend/src/api/auth.ts",
        ]
    )

    assert selection.render() == "all_pages,api,login"


def test_frontend_openapi_only_changes_select_types_only() -> None:
    """Frozen OpenAPI drift alone should run the generated-type check only."""
    selector = _load_selector_module()

    selection = selector._select_frontend_modes(["docs/api/openapi.frozen.json"])

    assert selection.render() == "types_only"


def test_frontend_generated_types_only_changes_select_types_only() -> None:
    """Regenerated frontend types alone should run the generated-type check only."""
    selector = _load_selector_module()

    selection = selector._select_frontend_modes(
        ["apps/frontend/src/api/generated/openapi-types.ts"]
    )

    assert selection.render() == "types_only"


def test_frontend_leader_page_changes_select_leader_tests() -> None:
    """Leader page changes should stay scoped to the leader workspace tests."""
    selector = _load_selector_module()

    selection = selector._select_frontend_modes(
        [
            "apps/frontend/src/pages/LeaderWorkspacePage.tsx",
            "apps/frontend/src/api/kpiSnapshots.ts",
        ]
    )

    assert selection.render() == "leader"


def test_browser_smoke_runs_for_login_and_candidate_apply_paths() -> None:
    """Auth and candidate apply edits should keep browser smoke enabled."""
    selector = _load_selector_module()

    assert selector._should_run_browser_smoke(["apps/frontend/src/pages/LoginPage.tsx"]) is True
    assert selector._should_run_browser_smoke(["apps/frontend/src/pages/CandidatePage.tsx"]) is True
    assert selector._should_run_browser_smoke(
        ["apps/frontend/src/pages/candidate/CandidateInterviewRegistrationPage.tsx"]
    ) is True
    assert selector._should_run_browser_smoke(
        ["scripts/browser_candidate_interview_smoke.py"]
    ) is True
    assert selector._should_run_browser_smoke(
        ["apps/frontend/src/pages/LeaderWorkspacePage.tsx"]
    ) is False
