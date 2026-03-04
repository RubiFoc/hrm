"""Database models for the auth domain."""

from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey
from hrm_backend.auth.models.staff_account import StaffAccount

__all__ = ["StaffAccount", "EmployeeRegistrationKey"]
