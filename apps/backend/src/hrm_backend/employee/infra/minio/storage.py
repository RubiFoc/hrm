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
        """Persist avatar binary payload in storage.

        Args:
            object_key: Object storage key for the avatar.
            data: Binary avatar payload.
            mime_type: MIME type for the payload.
            enable_sse: Whether to enable server-side encryption.
        """

    def get_object(self, *, object_key: str) -> bytes:
        """Load avatar binary payload from storage.

        Args:
            object_key: Object storage key for the avatar.

        Returns:
            bytes: Avatar binary payload.
        """

    def remove_object(self, *, object_key: str) -> None:
        """Remove avatar binary payload from storage.

        Args:
            object_key: Object storage key for the avatar.
        """


class MinioEmployeeAvatarStorage:
    """MinIO-backed avatar storage adapter using S3 API semantics."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
    ) -> None:
        """Initialize MinIO storage adapter.

        Args:
            endpoint: MinIO endpoint URL.
            access_key: MinIO access key.
            secret_key: MinIO secret key.
            bucket_name: Bucket name for avatar objects.

        Raises:
            HTTPException: If the MinIO client dependency is unavailable.
        """
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
        """Persist avatar content in MinIO bucket.

        Args:
            object_key: Object storage key for the avatar.
            data: Binary avatar payload.
            mime_type: MIME type for the payload.
            enable_sse: Whether to enable server-side encryption.

        Raises:
            HTTPException: If the upload fails.
        """
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
            raise service_unavailable("Object storage upload failed") from exc

    def get_object(self, *, object_key: str) -> bytes:
        """Load avatar content from MinIO bucket.

        Args:
            object_key: Object storage key for the avatar.

        Returns:
            bytes: Avatar binary payload.

        Raises:
            HTTPException: If the download fails.
        """
        response = None
        try:
            response = self._minio.get_object(self._bucket_name, object_key)
            return response.read()
        except Exception as exc:  # noqa: BLE001
            raise service_unavailable("Object storage download failed") from exc
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def remove_object(self, *, object_key: str) -> None:
        """Remove avatar content from MinIO bucket.

        Args:
            object_key: Object storage key for the avatar.

        Raises:
            HTTPException: If the delete fails.
        """
        try:
            self._minio.remove_object(self._bucket_name, object_key)
        except Exception as exc:  # noqa: BLE001
            raise service_unavailable("Object storage delete failed") from exc
