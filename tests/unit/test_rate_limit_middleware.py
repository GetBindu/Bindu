"""Unit tests for rate limit middleware."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.server.middleware.rate_limit import MemoryBackend, RateLimitMiddleware
from bindu.settings import app_settings


def _make_request(
    path: str = "/",
    method: str = "POST",
    headers: dict[str, str] | None = None,
) -> Request:
    """Create a request object for middleware testing."""
    headers = headers or {}
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
    ]

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
        "client": ("127.0.0.1", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    return Request(scope, receive)


@pytest.fixture(autouse=True)
def restore_rate_limit_settings():
    """Restore global rate-limit settings after each test."""
    original = app_settings.rate_limit.model_dump()
    yield
    for key, value in original.items():
        setattr(app_settings.rate_limit, key, value)


@pytest.mark.asyncio
async def test_memory_backend_resets_after_window():
    """Memory backend should reset count after window expiration."""
    backend = MemoryBackend()

    with patch(
        "bindu.server.middleware.rate_limit.time.time",
        side_effect=[100, 101, 161],
    ):
        count_1, reset_1 = await backend.increment("test-key", 60)
        count_2, reset_2 = await backend.increment("test-key", 60)
        count_3, reset_3 = await backend.increment("test-key", 60)

    assert count_1 == 1
    assert count_2 == 2
    assert count_3 == 1
    assert reset_1 == reset_2
    assert reset_3 > reset_2


@pytest.mark.asyncio
async def test_memory_backend_cleans_up_expired_keys():
    """Memory backend should remove expired keys during periodic cleanup."""
    backend = MemoryBackend(cleanup_interval=1)

    with patch(
        "bindu.server.middleware.rate_limit.time.time",
        side_effect=[100, 161],
    ):
        await backend.increment("expired-key", 60)
        await backend.increment("active-key", 60)

    assert "expired-key" not in backend._counters
    assert "active-key" in backend._counters


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429():
    """Middleware should reject requests above configured limit."""
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.backend = "memory"
    app_settings.rate_limit.a2a_limit = 2

    middleware = RateLimitMiddleware(MagicMock())
    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
    request = _make_request(path="/", method="POST")

    response_1 = await middleware.dispatch(request, call_next)
    response_2 = await middleware.dispatch(request, call_next)
    response_3 = await middleware.dispatch(request, call_next)

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 429
    assert call_next.call_count == 2

    payload = json.loads(response_3.body.decode("utf-8"))
    assert payload["error"] == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_success_response_includes_rate_limit_headers():
    """Allowed requests should include rate-limit response headers."""
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.backend = "memory"
    app_settings.rate_limit.a2a_limit = 3

    middleware = RateLimitMiddleware(MagicMock())
    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
    request = _make_request(path="/", method="POST")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "3"
    assert response.headers["X-RateLimit-Remaining"] == "2"
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_options_request_bypasses_rate_limit():
    """OPTIONS preflight requests should bypass the limiter."""
    app_settings.rate_limit.enabled = True

    middleware = RateLimitMiddleware(MagicMock())
    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
    request = _make_request(path="/", method="OPTIONS")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_x_forwarded_for_used_when_enabled():
    """When configured, X-Forwarded-For should be used for client identity."""
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.backend = "memory"
    app_settings.rate_limit.a2a_limit = 1
    app_settings.rate_limit.trust_x_forwarded_for = True

    middleware = RateLimitMiddleware(MagicMock())
    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

    request_a = _make_request(
        path="/",
        method="POST",
        headers={"X-Forwarded-For": "1.2.3.4"},
    )
    request_b = _make_request(
        path="/",
        method="POST",
        headers={"X-Forwarded-For": "1.2.3.4"},
    )
    request_c = _make_request(
        path="/",
        method="POST",
        headers={"X-Forwarded-For": "5.6.7.8"},
    )

    response_a = await middleware.dispatch(request_a, call_next)
    response_b = await middleware.dispatch(request_b, call_next)
    response_c = await middleware.dispatch(request_c, call_next)

    assert response_a.status_code == 200
    assert response_b.status_code == 429
    assert response_c.status_code == 200


@pytest.mark.asyncio
async def test_fail_open_on_backend_error():
    """When fail_open is true, backend failures should not block traffic."""
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.fail_open = True

    middleware = RateLimitMiddleware(MagicMock())
    middleware._backend = MagicMock()
    middleware._backend.increment = AsyncMock(side_effect=RuntimeError("backend down"))

    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
    request = _make_request(path="/", method="POST")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_fail_closed_on_backend_error():
    """When fail_open is false, backend failures should return 503."""
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.fail_open = False

    middleware = RateLimitMiddleware(MagicMock())
    middleware._backend = MagicMock()
    middleware._backend.increment = AsyncMock(side_effect=RuntimeError("backend down"))

    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))
    request = _make_request(path="/", method="POST")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 503
    call_next.assert_not_called()
