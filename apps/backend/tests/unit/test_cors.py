"""Unit tests for backend CORS behavior required by local frontend login UX."""

from __future__ import annotations

from collections.abc import Callable, Generator
from functools import partial
from typing import Any

import anyio.to_thread
import fastapi.concurrency
import pytest
import starlette.concurrency
from httpx import ASGITransport, AsyncClient

from hrm_backend.main import app


@pytest.fixture(autouse=True)
def inline_threadpool_patch() -> Generator[None, None, None]:
    """Avoid AnyIO threadpool deadlocks in in-process ASGI test requests."""
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


@pytest.mark.anyio
async def test_auth_login_preflight_allows_local_frontend_origin() -> None:
    """Verify auth login endpoint supports browser preflight from local frontend origin."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")
