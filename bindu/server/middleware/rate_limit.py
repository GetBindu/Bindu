"""Rate limiting middleware for backend HTTP endpoints."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from fnmatch import fnmatch
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.rate_limit")


class RateLimitBackend(ABC):
    """Backend contract for request counters."""

    @abstractmethod
    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Increment request count and return (count, reset_timestamp)."""


class MemoryBackend(RateLimitBackend):
    """In-memory rate limit backend.

    Suitable for local development and single-process deployments.
    """

    def __init__(self, cleanup_interval: int = 512) -> None:
        """Initialize an in-memory counter store.

        Args:
            cleanup_interval: Number of increment operations between
                opportunistic cleanup passes for expired keys.
        """
        self._counters: dict[str, tuple[int, int]] = {}
        self._lock = asyncio.Lock()
        # Opportunistically clear expired keys to avoid unbounded map growth.
        self._cleanup_interval = max(1, cleanup_interval)
        self._ops_since_cleanup = 0

    def _cleanup_expired(self, now: int) -> None:
        expired_keys = [
            key for key, (_, reset_at) in self._counters.items() if now >= reset_at
        ]
        for key in expired_keys:
            self._counters.pop(key, None)

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Increment a counter and return current count with reset timestamp.

        Args:
            key: Counter key scoped by policy and client identifier.
            window_seconds: Duration of the fixed window.

        Returns:
            Tuple of `(count, reset_at_epoch_seconds)`.
        """
        now = int(time.time())
        async with self._lock:
            self._ops_since_cleanup += 1
            if self._ops_since_cleanup >= self._cleanup_interval:
                self._cleanup_expired(now)
                self._ops_since_cleanup = 0

            count, reset_at = self._counters.get(key, (0, now + window_seconds))
            if now >= reset_at:
                count = 0
                reset_at = now + window_seconds

            count += 1
            self._counters[key] = (count, reset_at)
            return count, reset_at


class RedisBackend(RateLimitBackend):
    """Redis-backed rate limit backend for distributed deployments."""

    def __init__(self, redis_url: str) -> None:
        """Create a Redis client for distributed rate limit counters."""
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Increment a Redis counter and return count with reset timestamp."""
        now = int(time.time())
        count = int(await self._redis.incr(key))
        if count == 1:
            await self._redis.expire(key, window_seconds)
            return count, now + window_seconds

        ttl = await self._redis.ttl(key)
        if ttl is None or ttl < 0:
            await self._redis.expire(key, window_seconds)
            ttl = window_seconds
        return count, now + int(ttl)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """HTTP rate limiter with endpoint-specific policies."""

    def __init__(self, app) -> None:
        """Initialize middleware and select backend from app settings."""
        super().__init__(app)
        self._config = app_settings.rate_limit
        self._backend = self._create_backend() if self._config.enabled else None

    def _create_backend(self) -> RateLimitBackend:
        backend = self._config.backend
        if backend == "redis":
            redis_url = self._config.redis_url or app_settings.scheduler.redis_url
            if redis_url:
                logger.info("Rate limiting enabled with Redis backend")
                return RedisBackend(redis_url)
            logger.warning(
                "Rate limiting backend is 'redis' but no redis URL configured. "
                "Falling back to memory backend."
            )

        logger.info("Rate limiting enabled with in-memory backend")
        return MemoryBackend()

    def _get_client_id(self, request: Request) -> str:
        """Resolve a client identifier for rate limit keys."""
        if self._config.trust_x_forwarded_for:
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                first_ip = forwarded_for.split(",")[0].strip()
                if first_ip:
                    return first_ip

        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _resolve_policy(self, request: Request) -> tuple[str, int, int]:
        """Select rate-limit policy by endpoint and method."""
        method = request.method.upper()
        path = request.url.path
        window = self._config.window_seconds

        if method == "POST" and path == "/":
            return "a2a", self._config.a2a_limit, window
        if method == "POST" and path == "/agent/negotiation":
            return "negotiation", self._config.negotiation_limit, window
        if method == "POST" and path == "/api/start-payment-session":
            return "payment-session", self._config.payment_session_limit, window
        if method == "GET" and fnmatch(path, "/api/payment-status/*"):
            return "payment-status", self._config.payment_status_limit, window
        if method == "GET" and path == "/health":
            return "health", self._config.health_limit, window
        if method == "GET" and path == "/metrics":
            return "metrics", self._config.metrics_limit, window

        return "default", self._config.default_limit, window

    def _make_limit_response(
        self, limit: int, remaining: int, reset_at: int, retry_after: int
    ) -> JSONResponse:
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(reset_at),
        }
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
                "retry_after": retry_after,
            },
            headers=headers,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply per-endpoint rate limits and continue request processing."""
        if not self._config.enabled or self._backend is None:
            return await call_next(request)

        # Keep browser CORS preflight untouched.
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        policy_name, limit, window = self._resolve_policy(request)
        if limit <= 0:
            return await call_next(request)

        client_id = self._get_client_id(request)
        key = f"ratelimit:{policy_name}:{client_id}"

        try:
            count, reset_at = await self._backend.increment(key, window)
        except Exception as exc:
            logger.warning(f"Rate limiter backend error for {key}: {exc}")
            if self._config.fail_open:
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={
                    "error": "rate_limit_unavailable",
                    "message": "Rate limiting service unavailable",
                },
            )

        remaining = limit - count
        now = int(time.time())
        retry_after = max(0, reset_at - now)

        if count > limit:
            logger.warning(
                "Rate limit exceeded: "
                f"policy={policy_name} client={client_id} path={request.url.path}"
            )
            return self._make_limit_response(limit, remaining, reset_at, retry_after)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
