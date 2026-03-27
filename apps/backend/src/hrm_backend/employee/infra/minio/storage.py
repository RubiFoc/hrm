"""Object storage adapters for employee avatar binaries."""

from __future__ import annotations

import io
from typing import Protocol
from urllib.parse import urlparse

from hrm_backend.core.errors.http import service_unavailable


class EmployeeAvatarStorage(Protocol):
    """Storage client contract for employee avatar operations."""

    def put_object(
        self,
        *,
        object_key: str,
        data: bytes,
        mime_type: str,
        enable_sse: bool,
    ) -> None:
        """Persist avatar binary payload in object storage."""

    def get_object(self, *, object_key: str) -> bytes:
        """Load avatar binary payload by object key."""


class MinioEmployeeAvatarStorage:
    """MinIO-backed employee avatar storage adapter using S3 API semantics."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
    ) -> None:
        """Initialize MinIO storage adapter for employee avatars."""
        self._bucket_name = bucket_name
        parsed = urlparse(endpoint)
        client_endpoint = parsed.netloc or parsed.path
        secure = parsed.scheme.lower() == "https"

        try:
            from minio import Minio
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise service_unavailable("MinIO client dependency is not installed") from exc

        self._minio = Minio(
            client_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def put_object(
        self,
        *,
        object_key: str,
        data: bytes,
        mime_type: str,
        enable_sse: bool,
    ) -> None:
        """Persist avatar content in MinIO bucket."""
        sse = None
        if enable_sse:
            from minio.sse import SseS3

            sse = SseS3()

        try:
            self._minio.put_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=mime_type,
                sse=sse,
            )
        except Exception as exc:  # noqa: BLE001
            raise service_unavailable("Employee avatar upload failed") from exc

    def get_object(self, *, object_key: str) -> bytes:
        """Load avatar content from MinIO bucket."""
        response = None
        try:
            response = self._minio.get_object(self._bucket_name, object_key)
            return response.read()
        except Exception as exc:  # noqa: BLE001
            raise service_unavailable("Employee avatar download failed") from exc
        finally:
            if response is not None:
                response.close()
                response.release_conn()
