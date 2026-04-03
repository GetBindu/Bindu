"""Tests for RateLimitMiddleware sliding window logic."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from bindu.server.middleware.rate_limit import RateLimitMiddleware, _SlidingWindowCounter


# ---------------------------------------------------------------------------
# _SlidingWindowCounter unit tests
# ---------------------------------------------------------------------------

class TestSlidingWindowCounter:
    def test_counts_within_window(self):
        counter = _SlidingWindowCounter(window_seconds=10)
        now = time.time()
        assert counter.add_and_count(now) == 1
        assert counter.add_and_count(now + 1) == 2
        assert counter.add_and_count(now + 2) == 3

    def test_evicts_expired_timestamps(self):
        counter = _SlidingWindowCounter(window_seconds=5)
        now = time.time()
        # Add 3 requests at t=0
        for _ in range(3):
            counter.add_and_count(now)
        # Add 1 request 6 seconds later — old ones should be evicted
        count = counter.add_and_count(now + 6)
        assert count == 1

    def test_window_boundary_exact(self):
        counter = _SlidingWindowCounter(window_seconds=5)
        now = 1000.0
        counter.add_and_count(now)          # t=1000 (exactly at boundary, evicted)
        count = counter.add_and_count(now + 5)  # t=1005, window covers (1000, 1005]
        assert count == 1  # t=1000 is <= cutoff (1000.0), so evicted


# ---------------------------------------------------------------------------
# RateLimitMiddleware integration tests via TestClient
# ---------------------------------------------------------------------------

def _make_app(requests_per_window: int, window_seconds: int, exempt_paths=None):
    """Build a minimal Starlette app wrapped with RateLimitMiddleware."""
    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage), Route("/health", homepage)])
    kwargs = dict(
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )
    if exempt_paths is not None:
        kwargs["exempt_paths"] = frozenset(exempt_paths)
    app.add_middleware(RateLimitMiddleware, **kwargs)
    return app


class TestRateLimitMiddleware:
    def test_allows_requests_under_limit(self):
        app = _make_app(requests_per_window=5, window_seconds=60)
        client = TestClient(app, raise_server_exceptions=True)
        for _ in range(5):
            resp = client.get("/")
            assert resp.status_code == 200

    def test_blocks_requests_over_limit(self):
        app = _make_app(requests_per_window=3, window_seconds=60)
        client = TestClient(app, raise_server_exceptions=True)
        for _ in range(3):
            client.get("/")
        resp = client.get("/")
        assert resp.status_code == 429
        assert resp.json()["error"] == "rate_limit_exceeded"

    def test_retry_after_header_present(self):
        app = _make_app(requests_per_window=1, window_seconds=30)
        client = TestClient(app, raise_server_exceptions=True)
        client.get("/")
        resp = client.get("/")
        assert resp.status_code == 429
        assert resp.headers["retry-after"] == "30"

    def test_exempt_path_bypasses_limit(self):
        app = _make_app(
            requests_per_window=1,
            window_seconds=60,
            exempt_paths={"/health"},
        )
        client = TestClient(app, raise_server_exceptions=True)
        # Exhaust limit on /
        client.get("/")
        client.get("/")  # would be 429 on /
        # /health should always pass
        resp = client.get("/health")
        assert resp.status_code == 200
