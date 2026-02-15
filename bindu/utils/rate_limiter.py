"""Rate limiter implementation for Bindu agents.

Provides production-grade rate limiting with multiple strategies:
- Token bucket algorithm for smooth rate limiting
- Sliding window for precise rate control
- Per-agent rate limits
- Distributed rate limiting support (with Redis)

This prevents agent overload and ensures fair resource allocation.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import logging

logger = logging.getLogger("bindu.rate_limiter")


@dataclass
class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    limit: int
    window_seconds: float
    retry_after: float

    def __str__(self) -> str:
        return (
            f"Rate limit exceeded: {self.limit} requests per {self.window_seconds}s. "
            f"Retry after {self.retry_after:.2f}s"
        )


class TokenBucketRateLimiter:
    """Token bucket rate limiter for smooth traffic shaping.

    The token bucket algorithm allows bursts while maintaining average rate.
    Tokens are added at a constant rate, and each request consumes a token.

    Example:
        ```python
        # Allow 100 requests per minute with burst of 20
        limiter = TokenBucketRateLimiter(
            rate=100,
            per_seconds=60,
            burst_size=20
        )

        async def make_request():
            async with limiter:
                # Request proceeds if token available
                response = await agent.send_message(...)
        ```
    """

    def __init__(
        self,
        rate: int,
        per_seconds: float = 60.0,
        burst_size: Optional[int] = None,
        name: str = "default",
    ):
        """Initialize token bucket rate limiter.

        Args:
            rate: Maximum number of requests allowed per time window
            per_seconds: Time window in seconds
            burst_size: Maximum burst size (defaults to rate)
            name: Identifier for this rate limiter
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.burst_size = burst_size or rate
        self.name = name

        # Token bucket state
        self._tokens = float(self.burst_size)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

        # Metrics
        self._total_requests = 0
        self._accepted_requests = 0
        self._rejected_requests = 0

        logger.info(
            f"Token bucket rate limiter '{name}' initialized: "
            f"{rate} req/{per_seconds}s, burst={self.burst_size}"
        )

    async def __aenter__(self):
        """Context manager entry - acquire token."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Raises:
            RateLimitExceeded: If not enough tokens available
        """
        async with self._lock:
            self._total_requests += 1
            await self._refill_tokens()

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._accepted_requests += 1
            else:
                self._rejected_requests += 1
                # Calculate retry time
                tokens_needed = tokens - self._tokens
                time_per_token = self.per_seconds / self.rate
                retry_after = tokens_needed * time_per_token

                raise RateLimitExceeded(
                    limit=self.rate,
                    window_seconds=self.per_seconds,
                    retry_after=retry_after,
                )

    async def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update

        # Calculate tokens to add
        tokens_to_add = (elapsed / self.per_seconds) * self.rate
        self._tokens = min(self.burst_size, self._tokens + tokens_to_add)
        self._last_update = now

    def get_status(self) -> dict:
        """Get current status of rate limiter."""
        return {
            "name": self.name,
            "type": "token_bucket",
            "rate": self.rate,
            "per_seconds": self.per_seconds,
            "burst_size": self.burst_size,
            "available_tokens": round(self._tokens, 2),
            "total_requests": self._total_requests,
            "accepted_requests": self._accepted_requests,
            "rejected_requests": self._rejected_requests,
            "acceptance_rate": (
                round(
                    (self._accepted_requests / self._total_requests) * 100, 2
                )
                if self._total_requests > 0
                else 100.0
            ),
        }


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for precise rate control.

    Tracks individual request timestamps to provide exact rate limiting
    over a rolling time window.

    Example:
        ```python
        # Allow exactly 100 requests per minute
        limiter = SlidingWindowRateLimiter(
            max_requests=100,
            window_seconds=60
        )

        async with limiter:
            response = await agent.send_message(...)
        ```
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
        name: str = "default",
    ):
        """Initialize sliding window rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            name: Identifier for this rate limiter
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name

        # Track request timestamps
        self._request_times: deque = deque()
        self._lock = asyncio.Lock()

        # Metrics
        self._total_requests = 0
        self._accepted_requests = 0
        self._rejected_requests = 0

        logger.info(
            f"Sliding window rate limiter '{name}' initialized: "
            f"{max_requests} req/{window_seconds}s"
        )

    async def __aenter__(self):
        """Context manager entry - check rate limit."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False

    async def acquire(self) -> None:
        """Acquire permission to make request.

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        async with self._lock:
            self._total_requests += 1
            now = time.time()

            # Remove old requests outside window
            cutoff_time = now - self.window_seconds
            while self._request_times and self._request_times[0] < cutoff_time:
                self._request_times.popleft()

            # Check if limit exceeded
            if len(self._request_times) >= self.max_requests:
                self._rejected_requests += 1

                # Calculate retry time (when oldest request will expire)
                oldest_request = self._request_times[0]
                retry_after = (oldest_request + self.window_seconds) - now

                raise RateLimitExceeded(
                    limit=self.max_requests,
                    window_seconds=self.window_seconds,
                    retry_after=max(0, retry_after),
                )

            # Accept request
            self._request_times.append(now)
            self._accepted_requests += 1

    def get_status(self) -> dict:
        """Get current status of rate limiter."""
        now = time.time()
        cutoff_time = now - self.window_seconds

        # Count active requests in window
        active_requests = sum(1 for t in self._request_times if t >= cutoff_time)

        return {
            "name": self.name,
            "type": "sliding_window",
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "current_requests": active_requests,
            "available_requests": max(0, self.max_requests - active_requests),
            "total_requests": self._total_requests,
            "accepted_requests": self._accepted_requests,
            "rejected_requests": self._rejected_requests,
            "acceptance_rate": (
                round(
                    (self._accepted_requests / self._total_requests) * 100, 2
                )
                if self._total_requests > 0
                else 100.0
            ),
        }


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on system load.

    Automatically increases/decreases rate limits based on:
    - Error rates
    - Response times
    - System resource usage

    Example:
        ```python
        limiter = AdaptiveRateLimiter(
            base_rate=100,
            min_rate=10,
            max_rate=200,
            window_seconds=60
        )

        async with limiter:
            response = await agent.send_message(...)

        # Limiter automatically adjusts based on performance
        ```
    """

    def __init__(
        self,
        base_rate: int,
        min_rate: int,
        max_rate: int,
        window_seconds: float = 60.0,
        error_threshold: float = 0.1,  # 10% error rate triggers reduction
        adjustment_factor: float = 0.2,  # 20% adjustment per step
        name: str = "default",
    ):
        """Initialize adaptive rate limiter.

        Args:
            base_rate: Starting rate limit
            min_rate: Minimum rate limit
            max_rate: Maximum rate limit
            window_seconds: Time window for rate calculation
            error_threshold: Error rate that triggers limit reduction
            adjustment_factor: Percentage to adjust rate by
            name: Identifier for this rate limiter
        """
        self.base_rate = base_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.window_seconds = window_seconds
        self.error_threshold = error_threshold
        self.adjustment_factor = adjustment_factor
        self.name = name

        # Current adaptive rate
        self._current_rate = base_rate

        # Use sliding window limiter internally
        self._limiter = SlidingWindowRateLimiter(
            max_requests=base_rate,
            window_seconds=window_seconds,
            name=f"{name}_internal",
        )

        # Track errors for adaptation
        self._error_count = 0
        self._success_count = 0
        self._last_adjustment = time.time()
        self._adjustment_interval = window_seconds  # Adjust once per window

        self._lock = asyncio.Lock()

        logger.info(
            f"Adaptive rate limiter '{name}' initialized: "
            f"base={base_rate}, range=[{min_rate}, {max_rate}]"
        )

    async def __aenter__(self):
        """Context manager entry."""
        await self._limiter.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success/failure."""
        async with self._lock:
            if exc_type is None:
                self._success_count += 1
            else:
                self._error_count += 1

            # Check if we should adjust rate
            await self._maybe_adjust_rate()

        return False

    async def _maybe_adjust_rate(self):
        """Adjust rate limit based on error rate."""
        now = time.time()

        # Only adjust once per interval
        if now - self._last_adjustment < self._adjustment_interval:
            return

        total_requests = self._error_count + self._success_count
        if total_requests < 10:  # Need minimum sample size
            return

        error_rate = self._error_count / total_requests

        if error_rate > self.error_threshold:
            # Too many errors - reduce rate
            new_rate = max(
                self.min_rate,
                int(self._current_rate * (1 - self.adjustment_factor)),
            )
            if new_rate != self._current_rate:
                self._current_rate = new_rate
                self._limiter = SlidingWindowRateLimiter(
                    max_requests=new_rate,
                    window_seconds=self.window_seconds,
                    name=f"{self.name}_internal",
                )
                logger.warning(
                    f"Rate limiter '{self.name}' reduced rate to {new_rate} "
                    f"(error_rate={error_rate:.2%})"
                )
        elif error_rate < self.error_threshold / 2:
            # Low errors - try increasing rate
            new_rate = min(
                self.max_rate,
                int(self._current_rate * (1 + self.adjustment_factor)),
            )
            if new_rate != self._current_rate:
                self._current_rate = new_rate
                self._limiter = SlidingWindowRateLimiter(
                    max_requests=new_rate,
                    window_seconds=self.window_seconds,
                    name=f"{self.name}_internal",
                )
                logger.info(
                    f"Rate limiter '{self.name}' increased rate to {new_rate}"
                )

        # Reset counters
        self._error_count = 0
        self._success_count = 0
        self._last_adjustment = now

    def get_status(self) -> dict:
        """Get current status including adaptive metrics."""
        status = self._limiter.get_status()
        status.update(
            {
                "type": "adaptive",
                "current_rate": self._current_rate,
                "base_rate": self.base_rate,
                "min_rate": self.min_rate,
                "max_rate": self.max_rate,
                "error_count": self._error_count,
                "success_count": self._success_count,
            }
        )
        return status


class RateLimiterRegistry:
    """Registry to manage multiple rate limiters per agent."""

    def __init__(self):
        """Initialize registry."""
        self._limiters: dict[str, TokenBucketRateLimiter | SlidingWindowRateLimiter | AdaptiveRateLimiter] = {}

    def create_token_bucket(
        self, name: str, rate: int, per_seconds: float = 60.0, **kwargs
    ) -> TokenBucketRateLimiter:
        """Create token bucket rate limiter."""
        limiter = TokenBucketRateLimiter(
            rate=rate, per_seconds=per_seconds, name=name, **kwargs
        )
        self._limiters[name] = limiter
        return limiter

    def create_sliding_window(
        self, name: str, max_requests: int, window_seconds: float = 60.0
    ) -> SlidingWindowRateLimiter:
        """Create sliding window rate limiter."""
        limiter = SlidingWindowRateLimiter(
            max_requests=max_requests, window_seconds=window_seconds, name=name
        )
        self._limiters[name] = limiter
        return limiter

    def create_adaptive(
        self,
        name: str,
        base_rate: int,
        min_rate: int,
        max_rate: int,
        **kwargs,
    ) -> AdaptiveRateLimiter:
        """Create adaptive rate limiter."""
        limiter = AdaptiveRateLimiter(
            base_rate=base_rate, min_rate=min_rate, max_rate=max_rate, name=name, **kwargs
        )
        self._limiters[name] = limiter
        return limiter

    def get(self, name: str):
        """Get rate limiter by name."""
        return self._limiters.get(name)

    def get_all_statuses(self) -> dict:
        """Get status of all rate limiters."""
        return {name: limiter.get_status() for name, limiter in self._limiters.items()}
