"""Redis infrastructure helpers for auth domain."""

from hrm_backend.auth.redis.client import get_redis_client

__all__ = ["get_redis_client"]
