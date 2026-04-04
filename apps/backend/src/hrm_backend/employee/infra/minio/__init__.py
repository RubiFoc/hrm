"""MinIO adapters for employee avatar storage."""

from hrm_backend.employee.infra.minio.storage import (
    EmployeeAvatarStorage,
    MinioEmployeeAvatarStorage,
)

__all__ = ["EmployeeAvatarStorage", "MinioEmployeeAvatarStorage"]
