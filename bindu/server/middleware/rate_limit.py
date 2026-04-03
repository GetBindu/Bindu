"""Sliding-window rate limiting middleware for Bindu agents.

Tracks requests per client IP using a sliding window counter stored in memory.
Each window slot is 1 second wide; the window spans `window_seconds` slots.
No external dependencies — uses only stdlib `collections.deque` and `threading`.

Configuration (via agent config or app_settings.rate_limit):
    rate_limit:
        enabled: true
        requests_per_window: 60   # max requests allowed in the window
        window_seconds: 60        # rolling window size in seconds
        exempt_paths:             # paths that bypass rate limiting
          - /health
          - /metrics
          - /.well-known/agent.json
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.rate_limit")

_DEFAULT_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/healthz",
        "/metrics",
        "/.well-known/agent.json",
    }
)


class _SlidingWindowCounter:
    """Thread-safe sliding window request counter for a single client."""

    __slots__ = ("_lock", "_timestamps", "_window")

    def __init__(self, window_seconds: int) -> None:
        self._lock = threading.Lock()
        self._timestamps: deque[float] = deque()
        self._window = float(window_seconds)

    def add_and_count(self, now: float) -> int:
        """Record a new request and return the count within the current window."""
        cutoff = now - self._window
        with self._lock:
            # Evict timestamps outside the window
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()
            self._timestamps.append(now)
            return len(self._timestamps)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client-IP sliding window rate limiting middleware.

    Returns HTTP 429 with a Retry-After header when a client exceeds the
    configured request limit within the rolling window.

    Args:
        app: The ASGI application.
        requests_per_window: Maximum requests allowed per window per client.
        window_seconds: Rolling window size in seconds.
        exempt_paths: Set of URL paths that bypass rate limiting.
    """

    def __init__(
        self,
        app: Any,
        requests_per_window: int,
        window_seconds: int,
        exempt_paths: frozenset[str] = _DEFAULT_EXEMPT_PATHS,
    ) -> None:
        super().__init__(app)
        self._limit = requests_per_window
        self._window = window_seconds
        self._exempt = exempt_paths
        self._counters: dict[str, _SlidingWindowCounter] = {}
        self._lock = threading.Lock()

        logger.info(
            f"Rate limiting enabled: {requests_per_window} req/{window_seconds}s per client"
        )

    def _get_counter(self, client_ip: str) -> _SlidingWindowCounter:
        """Return (or lazily create) the counter for a client IP."""
        try:
            return self._counters[client_ip]
        except KeyError:
            with self._lock:
                # Double-checked locking
                if client_ip not in self._counters:
                    self._counters[client_ip] = _SlidingWindowCounter(self._window)
                return self._counters[client_ip]

    def _client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for proxied requests."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._exempt:
            return await call_next(request)

        client_ip = self._client_ip(request)
        counter = self._get_counter(client_ip)
        count = counter.add_and_count(time.time())

        if count > self._limit:
            logger.warning(
                f"Rate limit exceeded: client={client_ip} "
                f"count={count} limit={self._limit} window={self._window}s"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Too many requests. Limit is {self._limit} "
                        f"requests per {self._window} seconds."
                    ),
                },
                headers={"Retry-After": str(self._window)},
            )

        return await call_next(request)
