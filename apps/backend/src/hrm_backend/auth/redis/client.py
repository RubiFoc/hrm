"""Redis client provider for auth domain denylist infrastructure."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis

from hrm_backend.settings import AppSettings, get_settings

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]


@lru_cache(maxsize=4)
def _build_redis_client(redis_url: str) -> Redis:
    """Create and cache Redis client by URL.

    Args:
        redis_url: Redis connection URL.

    Returns:
        Redis: Configured Redis client instance.
    """
    return Redis.from_url(redis_url, decode_responses=False)


def get_redis_client(settings: SettingsDependency) -> Redis:
    """Provide Redis client for request-scoped dependencies.

    Args:
        settings: Auth runtime settings.

    Returns:
        Redis: Cached Redis client for configured URL.
    """
    return _build_redis_client(settings.redis_url)
