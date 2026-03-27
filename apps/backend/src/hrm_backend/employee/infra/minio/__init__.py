"""Employee avatar MinIO adapters."""

from hrm_backend.employee.infra.minio.storage import (
    EmployeeAvatarStorage,
    MinioEmployeeAvatarStorage,
)

__all__ = ["EmployeeAvatarStorage", "MinioEmployeeAvatarStorage"]
