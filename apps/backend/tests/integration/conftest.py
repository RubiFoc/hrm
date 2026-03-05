"""Integration test harness configuration and runtime safety patches.

This module centralizes integration-only pytest fixtures so API tests run with a
deterministic ASGI in-process transport across CI and local environments.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from functools import partial
from typing import Any

import anyio.to_thread
import fastapi.concurrency
import pytest
import starlette.concurrency


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Pin AnyIO backend for integration tests.

    Returns:
        str: Backend name used by ``pytest-anyio`` parametrization.
    """
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def inline_threadpool_patch() -> Generator[None, None, None]:
    """Patch threadpool helpers for deterministic in-process ASGI integration tests.

    In this runtime environment AnyIO threadpool workers can deadlock in test
    harnesses (``TestClient``/``ASGITransport``). Integration tests do not need
    true threadpool execution, so we run these call sites inline to keep suites
    deterministic and avoid hangs.
    """

    original_anyio_run_sync = anyio.to_thread.run_sync
    original_starlette_run_in_threadpool = starlette.concurrency.run_in_threadpool
    original_fastapi_run_in_threadpool = fastapi.concurrency.run_in_threadpool

    async def _run_sync_inline(
        func: Callable[..., Any],
        /,
        *args: Any,
        **_: Any,
    ) -> Any:
        return func(*args)

    async def _run_in_threadpool_inline(
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if kwargs:
            return partial(func, **kwargs)(*args)
        return func(*args)

    anyio.to_thread.run_sync = _run_sync_inline
    starlette.concurrency.run_in_threadpool = _run_in_threadpool_inline
    fastapi.concurrency.run_in_threadpool = _run_in_threadpool_inline
    try:
        yield
    finally:
        anyio.to_thread.run_sync = original_anyio_run_sync
        starlette.concurrency.run_in_threadpool = original_starlette_run_in_threadpool
        fastapi.concurrency.run_in_threadpool = original_fastapi_run_in_threadpool
