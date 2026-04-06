"""Authorization unit tests for role-permission matrix behavior."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from hrm_backend.main import get_rbac_matrix
from hrm_backend.rbac import (
    BackgroundAccessDeniedError,
    enforce_background_permission,
    evaluate_permission,
    parse_role,
)


class _InMemoryAuditService:
    """Simple audit service stub for background enforcement tests."""

    def __init__(self) -> None:
        """Initialize in-memory event sink."""
        self.events: list[dict[str, object]] = []

    def record_permission_decision(self, **payload: object) -> None:
        """Capture permission decision payload."""
        self.events.append(payload)


def test_parse_role_missing_value_returns_401() -> None:
    """Verify that empty role claim is rejected as unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        parse_role(None)

    assert exc_info.value.status_code == 401
    assert "Missing role claim" in str(exc_info.value.detail)


def test_parse_role_unknown_value_returns_403() -> None:
    """Verify that unknown role claim is rejected as forbidden."""
    with pytest.raises(HTTPException) as exc_info:
        parse_role("intern")

    assert exc_info.value.status_code == 403
    assert "Unknown role claim" in str(exc_info.value.detail)


def test_hr_can_create_vacancy_permission() -> None:
    """Verify that HR role has create permission for vacancies."""
    decision = evaluate_permission(role="hr", permission="vacancy:create")

    assert decision.allowed is True
    assert decision.reason is None


def test_manager_is_denied_for_vacancy_create_permission() -> None:
    """Verify centralized evaluator denies vacancy create for manager role."""
    decision = evaluate_permission(role="manager", permission="vacancy:create")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "vacancy:create" in decision.reason


def test_admin_can_upload_cv_permission() -> None:
    """Verify admin role contains CV upload permission."""
    decision = evaluate_permission(role="admin", permission="candidate_cv:upload")

    assert decision.allowed is True


def test_admin_can_read_audit_permission() -> None:
    """Verify admin role can read immutable audit events."""
    decision = evaluate_permission(role="admin", permission="audit:read")

    assert decision.allowed is True


def test_hr_is_denied_for_audit_read_permission() -> None:
    """Verify non-admin roles cannot access audit evidence query surface."""
    decision = evaluate_permission(role="hr", permission="audit:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "audit:read" in decision.reason


def test_hr_can_list_and_revoke_employee_keys_permissions() -> None:
    """Verify HR role can list and revoke employee registration keys."""
    list_decision = evaluate_permission(role="hr", permission="admin:employee_key:list")
    revoke_decision = evaluate_permission(role="hr", permission="admin:employee_key:revoke")

    assert list_decision.allowed is True
    assert revoke_decision.allowed is True


def test_hr_can_create_employee_profile_permission() -> None:
    """Verify HR role can bootstrap employee profiles from hire conversions."""
    decision = evaluate_permission(role="hr", permission="employee_profile:create")

    assert decision.allowed is True


def test_hr_can_manage_onboarding_templates_permissions() -> None:
    """Verify HR role can manage onboarding checklist templates."""
    create_decision = evaluate_permission(role="hr", permission="onboarding_template:create")
    update_decision = evaluate_permission(role="hr", permission="onboarding_template:update")

    assert create_decision.allowed is True
    assert update_decision.allowed is True


def test_hr_can_manage_onboarding_tasks_permissions() -> None:
    """Verify HR role can read, update, and backfill onboarding tasks."""
    list_decision = evaluate_permission(role="hr", permission="onboarding_task:list")
    update_decision = evaluate_permission(role="hr", permission="onboarding_task:update")
    backfill_decision = evaluate_permission(role="hr", permission="onboarding_task:backfill")

    assert list_decision.allowed is True
    assert update_decision.allowed is True
    assert backfill_decision.allowed is True


def test_hr_can_read_onboarding_dashboard_permission() -> None:
    """Verify HR role can access onboarding progress dashboard reads."""
    decision = evaluate_permission(role="hr", permission="onboarding_dashboard:read")

    assert decision.allowed is True


def test_manager_can_read_onboarding_dashboard_permission() -> None:
    """Verify manager role can access onboarding progress dashboard reads."""
    decision = evaluate_permission(role="manager", permission="onboarding_dashboard:read")

    assert decision.allowed is True


def test_manager_can_read_manager_workspace_permission() -> None:
    """Verify manager role can access the dedicated manager workspace read surface."""
    decision = evaluate_permission(role="manager", permission="manager_workspace:read")

    assert decision.allowed is True


def test_manager_can_read_and_update_notifications_permissions() -> None:
    """Verify manager role can access in-app notification read/update endpoints."""
    read_decision = evaluate_permission(role="manager", permission="notification:read")
    update_decision = evaluate_permission(role="manager", permission="notification:update")

    assert read_decision.allowed is True
    assert update_decision.allowed is True


def test_accountant_can_read_and_update_notifications_permissions() -> None:
    """Verify accountant role can access in-app notification read/update endpoints."""
    read_decision = evaluate_permission(role="accountant", permission="notification:read")
    update_decision = evaluate_permission(role="accountant", permission="notification:update")

    assert read_decision.allowed is True
    assert update_decision.allowed is True


def test_employee_can_access_and_update_self_service_portal_permissions() -> None:
    """Verify employee role can read and update self-service onboarding portal endpoints."""
    read_decision = evaluate_permission(role="employee", permission="employee_portal:read")
    update_decision = evaluate_permission(role="employee", permission="employee_portal:update")

    assert read_decision.allowed is True
    assert update_decision.allowed is True


def test_employee_can_read_employee_directory_permission() -> None:
    """Verify employee role can access employee directory reads."""
    decision = evaluate_permission(role="employee", permission="employee_directory:read")

    assert decision.allowed is True


def test_accountant_can_update_own_avatar_permission() -> None:
    """Verify accountant role can update own avatar."""
    decision = evaluate_permission(role="accountant", permission="employee_avatar:write")

    assert decision.allowed is True


def test_manager_is_denied_for_admin_avatar_permission() -> None:
    """Verify manager role cannot use admin avatar override permission."""
    decision = evaluate_permission(role="manager", permission="employee_avatar:admin")

    assert decision.allowed is False
    assert decision.reason is not None


def test_employee_can_create_referral_permission() -> None:
    """Verify employee role can submit referrals."""
    decision = evaluate_permission(role="employee", permission="referral:create")

    assert decision.allowed is True


def test_manager_can_request_and_confirm_raise_permissions() -> None:
    """Verify manager role can create, confirm, and read raise requests."""
    create_decision = evaluate_permission(role="manager", permission="compensation_raise:create")
    confirm_decision = evaluate_permission(role="manager", permission="compensation_raise:confirm")
    read_decision = evaluate_permission(role="manager", permission="compensation_raise:read")

    assert create_decision.allowed is True
    assert confirm_decision.allowed is True
    assert read_decision.allowed is True


def test_leader_can_approve_and_reject_raise_permissions() -> None:
    """Verify leader role can approve and reject raise requests."""
    approve_decision = evaluate_permission(role="leader", permission="compensation_raise:approve")
    reject_decision = evaluate_permission(role="leader", permission="compensation_raise:reject")
    read_decision = evaluate_permission(role="leader", permission="compensation_raise:read")

    assert approve_decision.allowed is True
    assert reject_decision.allowed is True
    assert read_decision.allowed is True


def test_hr_can_manage_salary_bands_permission() -> None:
    """Verify HR role can write salary bands."""
    decision = evaluate_permission(role="hr", permission="salary_band:write")

    assert decision.allowed is True


def test_accountant_can_write_bonus_permission() -> None:
    """Verify accountant role can write bonus entries."""
    decision = evaluate_permission(role="accountant", permission="bonus:write")

    assert decision.allowed is True


def test_manager_can_read_compensation_table_permission() -> None:
    """Verify manager role can read compensation table."""
    decision = evaluate_permission(role="manager", permission="compensation:read")

    assert decision.allowed is True


def test_hr_can_read_and_review_referrals_permissions() -> None:
    """Verify HR role can read and review referrals."""
    read_decision = evaluate_permission(role="hr", permission="referral:read")
    review_decision = evaluate_permission(role="hr", permission="referral:review")

    assert read_decision.allowed is True
    assert review_decision.allowed is True


def test_manager_can_read_and_review_referrals_permissions() -> None:
    """Verify manager role can read and review referrals."""
    read_decision = evaluate_permission(role="manager", permission="referral:read")
    review_decision = evaluate_permission(role="manager", permission="referral:review")

    assert read_decision.allowed is True
    assert review_decision.allowed is True


def test_leader_can_read_kpi_snapshot_permission() -> None:
    """Verify leader role can read monthly KPI snapshot reports."""
    decision = evaluate_permission(role="leader", permission="kpi_snapshot:read")

    assert decision.allowed is True


def test_leader_is_denied_for_kpi_snapshot_rebuild_permission() -> None:
    """Verify leader role cannot rebuild KPI snapshots."""
    decision = evaluate_permission(role="leader", permission="kpi_snapshot:rebuild")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "kpi_snapshot:rebuild" in decision.reason


def test_hr_can_manage_automation_rules_permissions() -> None:
    """Verify HR role can manage automation rules."""
    create_decision = evaluate_permission(role="hr", permission="automation_rule:create")
    list_decision = evaluate_permission(role="hr", permission="automation_rule:list")
    update_decision = evaluate_permission(role="hr", permission="automation_rule:update")
    activate_decision = evaluate_permission(role="hr", permission="automation_rule:activate")

    assert create_decision.allowed is True
    assert list_decision.allowed is True
    assert update_decision.allowed is True
    assert activate_decision.allowed is True


def test_manager_is_denied_for_automation_rule_list_permission() -> None:
    """Verify manager role cannot access automation control plane APIs."""
    decision = evaluate_permission(role="manager", permission="automation_rule:list")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "automation_rule:list" in decision.reason


def test_hr_can_read_automation_execution_logs_permissions() -> None:
    """Verify HR role can read automation execution logs."""
    list_decision = evaluate_permission(role="hr", permission="automation_execution:list")
    read_decision = evaluate_permission(role="hr", permission="automation_execution:read")

    assert list_decision.allowed is True
    assert read_decision.allowed is True


def test_manager_is_denied_for_automation_execution_read_permission() -> None:
    """Verify manager role cannot access automation execution logs."""
    decision = evaluate_permission(role="manager", permission="automation_execution:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "automation_execution:read" in decision.reason


def test_manager_is_denied_for_employee_key_list_permission() -> None:
    """Verify manager role is denied for employee-key list permission."""
    decision = evaluate_permission(role="manager", permission="admin:employee_key:list")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "admin:employee_key:list" in decision.reason


def test_manager_is_denied_for_employee_profile_read_permission() -> None:
    """Verify manager role is denied for staff-only employee profile reads."""
    decision = evaluate_permission(role="manager", permission="employee_profile:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "employee_profile:read" in decision.reason


def test_manager_is_denied_for_vacancy_read_permission() -> None:
    """Verify manager role cannot reuse the HR vacancy list/read endpoints directly."""
    decision = evaluate_permission(role="manager", permission="vacancy:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "vacancy:read" in decision.reason


def test_manager_is_denied_for_interview_manage_permission() -> None:
    """Verify manager role does not keep broad HR interview mutation permissions."""
    decision = evaluate_permission(role="manager", permission="interview:manage")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "interview:manage" in decision.reason


def test_hr_is_denied_for_employee_portal_read_permission() -> None:
    """Verify staff roles cannot call employee-only self-service onboarding endpoints."""
    decision = evaluate_permission(role="hr", permission="employee_portal:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "employee_portal:read" in decision.reason


def test_manager_is_denied_for_onboarding_template_list_permission() -> None:
    """Verify manager role is denied for staff-only onboarding template reads."""
    decision = evaluate_permission(role="manager", permission="onboarding_template:list")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "onboarding_template:list" in decision.reason


def test_manager_is_denied_for_onboarding_task_list_permission() -> None:
    """Verify manager role is denied for staff-only onboarding task reads."""
    decision = evaluate_permission(role="manager", permission="onboarding_task:list")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "onboarding_task:list" in decision.reason


def test_hr_is_denied_for_notification_read_permission() -> None:
    """Verify HR role cannot access manager/accountant notification endpoints in v1."""
    decision = evaluate_permission(role="hr", permission="notification:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "notification:read" in decision.reason


def test_employee_is_denied_for_onboarding_dashboard_permission() -> None:
    """Verify employee role cannot access staff onboarding dashboard endpoints."""
    decision = evaluate_permission(role="employee", permission="onboarding_dashboard:read")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "onboarding_dashboard:read" in decision.reason


def test_background_enforcement_records_denied_decision() -> None:
    """Verify background permission check denies and records audit decision."""
    audit_service = _InMemoryAuditService()

    with pytest.raises(BackgroundAccessDeniedError):
        enforce_background_permission(
            subject_id="job-user",
            role="manager",
            permission="vacancy:create",
            audit_service=audit_service,  # type: ignore[arg-type]
            correlation_id="job-correlation-1",
        )

    assert len(audit_service.events) == 1
    assert audit_service.events[0]["allowed"] is False
    assert audit_service.events[0]["permission"] == "vacancy:create"
    assert audit_service.events[0]["correlation_id"] == "job-correlation-1"


def test_background_enforcement_records_invalid_role_reason() -> None:
    """Verify invalid background role produces explicit audit deny reason."""
    audit_service = _InMemoryAuditService()

    with pytest.raises(BackgroundAccessDeniedError):
        enforce_background_permission(
            subject_id="job-user",
            role="intern",
            permission="vacancy:create",
            audit_service=audit_service,  # type: ignore[arg-type]
            correlation_id="job-correlation-2",
        )

    assert len(audit_service.events) == 1
    assert audit_service.events[0]["allowed"] is False
    assert audit_service.events[0]["reason"] == "Unknown role claim: intern"


def test_rbac_matrix_contains_all_phase1_roles() -> None:
    """Verify exported RBAC matrix includes full phase-1 role set."""
    matrix = get_rbac_matrix()

    assert set(matrix) == {
        "admin",
        "hr",
        "manager",
        "employee",
        "leader",
        "accountant",
    }
