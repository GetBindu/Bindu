"""Circuit Breaker pattern for failure isolation in distributed systems.

Integrates with Bindu's existing Tenacity-based retry system to prevent
retry storms and cascading failures. When a downstream service fails
repeatedly, the circuit breaker trips OPEN, causing calls to fail-fast
without consuming retry attempts.

State Machine:
    CLOSED  → (failures >= threshold) → OPEN
    OPEN    → (recovery_timeout elapsed) → HALF_OPEN
    HALF_OPEN → (success) → CLOSED
    HALF_OPEN → (failure) → OPEN

Configuration via environment variables:
    BINDU_CB_ENABLED=true
    BINDU_CB_FAILURE_THRESHOLD=3
    BINDU_CB_RECOVERY_TIMEOUT=30
    BINDU_CB_SUCCESS_THRESHOLD=1
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.circuit_breaker")

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted while the circuit is OPEN.

    Attributes:
        operation_name: Name of the protected operation.
        retry_after: Seconds until the circuit transitions to HALF_OPEN.
    """

    def __init__(self, operation_name: str, retry_after: float = 0.0) -> None:
        self.operation_name = operation_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker is OPEN for '{operation_name}'. "
            f"Retry after {retry_after:.1f}s."
        )


class CircuitBreaker:
    """Per-operation circuit breaker with async safety.

    Each instance tracks failures for a single logical operation
    (e.g., ``storage_update``, ``api_call_openai``) and transitions
    between CLOSED → OPEN → HALF_OPEN → CLOSED based on observed
    success/failure patterns.

    Args:
        name: Human-readable operation identifier used in logs.
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait in OPEN before allowing a probe.
        success_threshold: Consecutive successes in HALF_OPEN to close.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current circuit state (read-only snapshot, not lock-protected)."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises:
            CircuitBreakerOpenError: If the circuit is OPEN and the
                recovery timeout has not yet elapsed.
        """
        async with self._lock:
            self._maybe_transition_to_half_open()

            if not self._is_call_allowed():
                retry_after = self._seconds_until_half_open()
                raise CircuitBreakerOpenError(self.name, retry_after)

        # Execute outside the lock so concurrent calls are not serialised.
        try:
            result = await func(*args, **kwargs)
        except Exception:
            async with self._lock:
                self._record_failure()
            raise
        else:
            async with self._lock:
                self._record_success()
            return result

    def reset(self) -> None:
        """Force-reset the circuit to CLOSED (useful in tests)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    # ------------------------------------------------------------------
    # Internal helpers (must be called under self._lock)
    # ------------------------------------------------------------------

    def _is_call_allowed(self) -> bool:
        """Check whether a call can proceed given the current state."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return True
        # OPEN – blocked
        return False

    def _maybe_transition_to_half_open(self) -> None:
        """Transition OPEN → HALF_OPEN if the recovery timeout has elapsed."""
        if self._state != CircuitState.OPEN:
            return
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self.recovery_timeout:
            self._transition(CircuitState.HALF_OPEN)

    def _record_failure(self) -> None:
        """Record a failure and potentially trip the circuit."""
        self._failure_count += 1
        self._success_count = 0
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately re-opens the circuit.
            self._transition(CircuitState.OPEN)
        elif (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self.failure_threshold
        ):
            self._transition(CircuitState.OPEN)

    def _record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            # Reset failure counter on success in normal operation.
            self._failure_count = 0

    def _transition(self, new_state: CircuitState) -> None:
        """Log and apply a state transition."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0

        logger.info(
            f"Circuit breaker [{self.name}] {old_state.value} → {new_state.value} "
            f"(failures={self._failure_count})"
        )

    def _seconds_until_half_open(self) -> float:
        """Remaining seconds before the circuit will probe."""
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)


# ======================================================================
# Global registry — one CircuitBreaker per operation name
# ======================================================================

_registry: dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


async def get_circuit_breaker(
    name: str,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
    success_threshold: int | None = None,
) -> CircuitBreaker:
    """Return the ``CircuitBreaker`` for *name*, creating it if needed.

    Default thresholds are pulled from ``app_settings.circuit_breaker``
    when not explicitly provided.
    """
    from bindu.settings import app_settings

    async with _registry_lock:
        if name not in _registry:
            cb_settings = app_settings.circuit_breaker
            _registry[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold or cb_settings.failure_threshold,
                recovery_timeout=recovery_timeout or cb_settings.recovery_timeout,
                success_threshold=success_threshold or cb_settings.success_threshold,
            )
        return _registry[name]


def get_circuit_breaker_sync(name: str) -> CircuitBreaker | None:
    """Non-async lookup — returns ``None`` if not yet registered."""
    return _registry.get(name)


def reset_all_circuit_breakers() -> None:
    """Reset every circuit breaker to CLOSED (test helper)."""
    for cb in _registry.values():
        cb.reset()


def clear_circuit_breaker_registry() -> None:
    """Remove all registered circuit breakers (test helper)."""
    _registry.clear()


# ======================================================================
# Decorator for integrating with retry wrappers
# ======================================================================


def with_circuit_breaker(operation_name: str | None = None) -> Callable[[F], F]:
    """Wrap an async function with circuit breaker protection.

    When ``BINDU_CB_ENABLED`` is ``false`` (the default), this decorator
    is a no-op passthrough, preserving full backward compatibility.

    Args:
        operation_name: Logical name for the circuit breaker instance.
            Defaults to the wrapped function's ``__qualname__``.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from bindu.settings import app_settings

            if not app_settings.circuit_breaker.enabled:
                return await func(*args, **kwargs)

            cb_name = operation_name or func.__qualname__
            cb = await get_circuit_breaker(cb_name)
            return await cb.call(func, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
