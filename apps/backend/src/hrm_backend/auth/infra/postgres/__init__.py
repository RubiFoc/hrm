"""PostgreSQL adapters for auth domain."""

from hrm_backend.auth.infra.postgres.employee_registration_key_dao import EmployeeRegistrationKeyDAO
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO

__all__ = ["StaffAccountDAO", "EmployeeRegistrationKeyDAO"]
