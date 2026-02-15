"""Circuit breaker implementation for Bindu agents.

This module provides a production-grade circuit breaker pattern to protect agents from
cascading failures when communicating with other agents or external services.

Features:
- Automatic failure detection and recovery
- Configurable thresholds and timeouts
- Half-open state for gradual recovery
- Metrics tracking for observability
- Thread-safe implementation for concurrent requests
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import logging

logger = logging.getLogger("bindu.circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation - requests pass through
    OPEN = "open"  # Failure threshold exceeded - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered - limited requests


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Requests rejected due to open circuit
    state_transitions: dict[str, int] = field(
        default_factory=lambda: {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0,
        }
    )
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "success_rate": round(self.success_rate(), 2),
            "state_transitions": self.state_transitions,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Production-grade circuit breaker for agent-to-agent communication.

    The circuit breaker prevents cascading failures by:
    1. Monitoring failure rates
    2. Opening the circuit when threshold is exceeded
    3. Failing fast while circuit is open
    4. Gradually testing recovery in half-open state

    Example:
        ```python
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=RequestException
        )

        async def call_agent():
            async with breaker:
                response = await agent.send_message(...)
                return response
        ```
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        success_threshold: int = 2,
        expected_exception: type[Exception] = Exception,
        name: str = "default",
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max concurrent calls in half-open state
            success_threshold: Successes needed in half-open to close circuit
            expected_exception: Exception type to count as failure
            name: Identifier for this circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        # Track recent failures for analysis
        self._recent_failures: deque = deque(maxlen=failure_threshold * 2)

        # Metrics
        self.metrics = CircuitBreakerMetrics()

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    async def __aenter__(self):
        """Context manager entry - check if call should proceed."""
        await self._before_call()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success or failure."""
        if exc_type is None:
            await self._on_success()
        elif isinstance(exc_val, self.expected_exception):
            await self._on_failure(exc_val)
        # Don't suppress exceptions
        return False

    async def _before_call(self):
        """Check circuit state before allowing a call."""
        async with self._lock:
            self.metrics.total_requests += 1

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self._should_attempt_reset():
                    await self._transition_to_half_open()
                else:
                    self.metrics.rejected_requests += 1
                    time_remaining = (
                        self.recovery_timeout
                        - (time.time() - self._last_failure_time)
                    )
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry in {time_remaining:.1f}s"
                    )

            elif self._state == CircuitState.HALF_OPEN:
                # Limit concurrent calls in half-open state
                if self._half_open_calls >= self.half_open_max_calls:
                    self.metrics.rejected_requests += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF-OPEN. "
                        f"Max concurrent calls reached ({self.half_open_max_calls})"
                    )
                self._half_open_calls += 1

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls -= 1

                if self._success_count >= self.success_threshold:
                    await self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _on_failure(self, exception: Exception):
        """Handle failed call."""
        async with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.time()
            self._last_failure_time = time.time()
            self._failure_count += 1

            # Track recent failures
            self._recent_failures.append(
                {"time": time.time(), "error": str(exception), "type": type(exception).__name__}
            )

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
                await self._transition_to_open()
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return False
        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    async def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        if self._state != CircuitState.OPEN:
            prev_state = self._state.value
            self._state = CircuitState.OPEN
            self.metrics.state_transitions[f"{prev_state}_to_open"] += 1
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
            )

    async def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0
        self.metrics.state_transitions["open_to_half_open"] += 1
        logger.info(f"Circuit breaker '{self.name}' entering HALF-OPEN state")

    async def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self.metrics.state_transitions["half_open_to_closed"] += 1
        logger.info(f"Circuit breaker '{self.name}' closed - service recovered")

    async def force_open(self):
        """Manually open the circuit (for testing or maintenance)."""
        async with self._lock:
            await self._transition_to_open()

    async def force_close(self):
        """Manually close the circuit (for testing or recovery)."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info(f"Circuit breaker '{self.name}' manually closed")

    def get_status(self) -> dict[str, Any]:
        """Get detailed status of circuit breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "recent_failures": list(self._recent_failures),
            "metrics": self.metrics.to_dict(),
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "half_open_max_calls": self.half_open_max_calls,
                "success_threshold": self.success_threshold,
            },
        }


class CircuitBreakerRegistry:
    """Registry to manage multiple circuit breakers.

    Example:
        ```python
        registry = CircuitBreakerRegistry()

        # Create circuit breaker for specific agent
        agent_breaker = registry.get_or_create("agent_123", failure_threshold=3)

        # Get all circuit breaker statuses
        statuses = registry.get_all_statuses()
        ```
    """

    def __init__(self):
        """Initialize registry."""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        **kwargs,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker.

        Args:
            name: Unique identifier for the circuit breaker
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            **kwargs: Additional arguments for CircuitBreaker

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                **kwargs,
            )
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def remove(self, name: str) -> bool:
        """Remove circuit breaker from registry."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False

    def get_all_statuses(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    def get_open_circuits(self) -> list[str]:
        """Get list of circuit breaker names that are currently open."""
        return [name for name, breaker in self._breakers.items() if breaker.is_open]

    async def reset_all(self):
        """Reset all circuit breakers to closed state."""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.force_close()
