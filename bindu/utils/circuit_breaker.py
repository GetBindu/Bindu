"""Circuit Breaker pattern for preventing retry storms.

A circuit breaker prevents cascading failures by stopping retry attempts
when a service is consistently unavailable.
"""

from __future__ import annotations

import time
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional, TypeVar

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.circuit_breaker")

F = TypeVar("F", bound=Callable[..., Any])

# Global registry of circuit breakers
_circuit_breakers: dict[str, "CircuitBreaker"] = {}
_registry_lock = Lock()


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker to prevent retry storms."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """Initialize circuit breaker with given configuration.

        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before testing recovery
            success_threshold: Successes needed to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = Lock()
        logger.info(f"Circuit breaker '{name}' initialized")

    def _should_attempt_reset(self) -> bool:
        """Check if we should test recovery."""
        if self.state == CircuitState.OPEN and self.last_failure_time:
            time_since_failure = time.time() - self.last_failure_time
            return time_since_failure >= self.recovery_timeout
        return False

    def _on_success(self) -> None:
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
                    logger.info(f"Circuit '{self.name}': CLOSED (recovered)")

    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                logger.warning(f"Circuit '{self.name}': Back to OPEN")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.error(f"Circuit '{self.name}': OPEN (too many failures)")

    async def call_async(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute async function with circuit breaker protection."""
        if self._should_attempt_reset():
            with self.lock:
                if self.state == CircuitState.OPEN:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit '{self.name}': HALF_OPEN (testing)")
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f"Circuit '{self.name}' is OPEN")
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def protect_async(self, func: F) -> F:
        """Decorate an async function with circuit breaker protection."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.call_async(func, *args, **kwargs)

        return wrapper  # type: ignore

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state manually."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            logger.info(f"Circuit '{self.name}': Reset to CLOSED")


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is OPEN."""

    pass


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 2,
) -> CircuitBreaker:
    """Get or create a named circuit breaker from the global registry.

    Args:
        name: Circuit breaker identifier
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before testing recovery
        success_threshold: Successes needed to close circuit

    Returns:
        CircuitBreaker instance

    Example:
        # In module A:
        circuit = get_circuit_breaker("external_api")

        # In module B (gets same instance):
        circuit = get_circuit_breaker("external_api")
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )
        return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all registered circuit breakers to CLOSED state."""
    with _registry_lock:
        for circuit in _circuit_breakers.values():
            circuit.reset()
        logger.info("All circuit breakers reset")
