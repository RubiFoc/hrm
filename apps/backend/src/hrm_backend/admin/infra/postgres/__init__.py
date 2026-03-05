"""PostgreSQL adapters for admin domain."""

from hrm_backend.admin.dao.employee_registration_key_dao import AdminEmployeeRegistrationKeyDAO
from hrm_backend.admin.dao.staff_account_dao import AdminStaffAccountDAO

__all__ = ["AdminStaffAccountDAO", "AdminEmployeeRegistrationKeyDAO"]
