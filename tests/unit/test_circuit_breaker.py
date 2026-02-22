"""Unit tests for the Circuit Breaker module.

Tests cover all state transitions, async safety, configuration loading,
disabled mode, and integration with retry decorators.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from bindu.settings import app_settings
from bindu.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    clear_circuit_breaker_registry,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from bindu.utils.retry import retry_worker_operation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset circuit breaker registry between tests."""
    clear_circuit_breaker_registry()
    yield
    clear_circuit_breaker_registry()


def _make_cb(
    name: str = "test",
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0,
    success_threshold: int = 1,
) -> CircuitBreaker:
    """Shortcut to build a CircuitBreaker with test-friendly defaults."""
    return CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
    )


# ===========================================================================
# 1. CLOSED → OPEN transition
# ===========================================================================


class TestClosedToOpen:
    """The circuit should open after reaching the failure threshold."""

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = _make_cb(failure_threshold=3)

        call_count = 0

        async def failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("down")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self):
        cb = _make_cb(failure_threshold=3)

        async def failing():
            raise ConnectionError("down")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing)

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_resets_failure_count_on_success(self):
        cb = _make_cb(failure_threshold=3)

        async def success():
            return "ok"

        async def failing():
            raise ConnectionError("down")

        # Two failures, then a success → counter resets
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing)

        await cb.call(success)
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


# ===========================================================================
# 2. OPEN blocks execution
# ===========================================================================


class TestOpenBlocks:
    """Calls should be rejected immediately when the circuit is OPEN."""

    @pytest.mark.asyncio
    async def test_raises_circuit_breaker_open_error(self):
        cb = _make_cb(failure_threshold=1, recovery_timeout=600)

        async def failing():
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        # Subsequent call is blocked
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(failing)

        assert exc_info.value.operation_name == "test"
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_blocked_call_does_not_execute_function(self):
        cb = _make_cb(failure_threshold=1, recovery_timeout=600)
        call_count = 0

        async def tracked_fn():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await cb.call(tracked_fn)

        assert call_count == 1

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(tracked_fn)

        # Function was NOT called again
        assert call_count == 1


# ===========================================================================
# 3. OPEN → HALF_OPEN after timeout
# ===========================================================================


class TestOpenToHalfOpen:
    """After recovery_timeout, the circuit should transition to HALF_OPEN."""

    @pytest.mark.asyncio
    async def test_transitions_after_timeout(self):
        cb = _make_cb(failure_threshold=1, recovery_timeout=0.1)

        async def failing():
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        async def success():
            return "recovered"

        result = await cb.call(success)
        assert result == "recovered"
        # Should have transitioned through HALF_OPEN → CLOSED
        assert cb.state == CircuitState.CLOSED


# ===========================================================================
# 4. HALF_OPEN → CLOSED on success
# ===========================================================================


class TestHalfOpenToClosedOnSuccess:
    """Successful calls in HALF_OPEN should close the circuit."""

    @pytest.mark.asyncio
    async def test_closes_after_success_threshold(self):
        cb = _make_cb(
            failure_threshold=1,
            recovery_timeout=0.05,
            success_threshold=2,
        )

        async def failing():
            raise ConnectionError("down")

        async def success():
            return "ok"

        # Trip to OPEN
        with pytest.raises(ConnectionError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.1)

        # First success — still HALF_OPEN
        await cb.call(success)
        assert cb.state == CircuitState.HALF_OPEN

        # Second success — closes
        await cb.call(success)
        assert cb.state == CircuitState.CLOSED


# ===========================================================================
# 5. HALF_OPEN → OPEN on failure
# ===========================================================================


class TestHalfOpenToOpenOnFailure:
    """Any failure in HALF_OPEN should re-open the circuit immediately."""

    @pytest.mark.asyncio
    async def test_reopens_on_failure(self):
        cb = _make_cb(failure_threshold=1, recovery_timeout=0.05)

        async def failing():
            raise ConnectionError("still down")

        # Trip to OPEN
        with pytest.raises(ConnectionError):
            await cb.call(failing)

        await asyncio.sleep(0.1)

        # Now HALF_OPEN — but fails again
        with pytest.raises(ConnectionError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN


# ===========================================================================
# 6. Async safety test
# ===========================================================================


class TestAsyncSafety:
    """Concurrent calls should not corrupt circuit breaker state."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_do_not_corrupt_state(self):
        cb = _make_cb(failure_threshold=5, recovery_timeout=600)

        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            # Simulate some async work
            await asyncio.sleep(0.01)
            raise ConnectionError("concurrent failure")

        # Launch many concurrent calls
        tasks = [cb.call(flaky) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should have raised ConnectionError (none should crash)
        for r in results:
            assert isinstance(r, (ConnectionError, CircuitBreakerOpenError))

        # State should be OPEN after >= 5 failures
        assert cb.state == CircuitState.OPEN


# ===========================================================================
# 7. Config loading test
# ===========================================================================


class TestConfigLoading:
    """Circuit breaker default settings should load from app_settings."""

    def test_default_settings(self):
        """Settings should load with correct types and sensible values."""
        cb_settings = app_settings.circuit_breaker
        assert isinstance(cb_settings.enabled, bool)
        assert cb_settings.failure_threshold >= 1
        assert cb_settings.recovery_timeout > 0
        assert cb_settings.success_threshold >= 1

    @pytest.mark.asyncio
    async def test_registry_uses_settings(self):
        """get_circuit_breaker should create instances from settings."""
        cb = await get_circuit_breaker("config_test")
        assert cb.failure_threshold == app_settings.circuit_breaker.failure_threshold
        assert cb.recovery_timeout == app_settings.circuit_breaker.recovery_timeout
        assert cb.success_threshold == app_settings.circuit_breaker.success_threshold


# ===========================================================================
# 8. Disabled mode test
# ===========================================================================


class TestDisabledMode:
    """When CB is disabled, the circuit breaker must be a transparent no-op."""

    @pytest.mark.asyncio
    async def test_passthrough_when_disabled(self):
        """With CB disabled (default), retry decorators work exactly as before."""

        @retry_worker_operation(max_attempts=2, min_wait=0.1, max_wait=0.2)
        async def successful_op():
            return "pass-through"

        result = await successful_op()
        assert result == "pass-through"

    @pytest.mark.asyncio
    async def test_passthrough_retries_when_disabled(self):
        """Retries still work normally when CB is disabled."""
        call_count = 0

        @retry_worker_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("temp")
            return "ok"

        result = await flaky_op()
        assert result == "ok"
        assert call_count == 2


# ===========================================================================
# 9. Integration test with retry wrapper
# ===========================================================================


class TestRetryIntegration:
    """When CB is enabled, retry decorators should respect circuit state."""

    @pytest.mark.asyncio
    async def test_retry_with_cb_enabled_fails_fast_when_open(self):
        """After tripping the circuit, retries are skipped entirely.

        The circuit breaker wraps the entire retry loop, so each full
        retry-exhaustion counts as 1 circuit-level failure.  With
        failure_threshold=2, we need 2 full failed invocations before
        the circuit opens on the 3rd call.
        """
        call_count = 0

        @retry_worker_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("down")

        # Temporarily enable CB
        with patch.object(
            app_settings.circuit_breaker, "enabled", True
        ), patch.object(
            app_settings.circuit_breaker, "failure_threshold", 2
        ), patch.object(
            app_settings.circuit_breaker, "recovery_timeout", 600
        ):
            # First invocation — retries exhaust, CB records 1 failure
            with pytest.raises(ConnectionError):
                await always_fails()

            # Second invocation — retries exhaust, CB records 2nd failure → OPEN
            with pytest.raises(ConnectionError):
                await always_fails()

            calls_after_open = call_count

            # Third invocation — circuit is OPEN, fails immediately
            with pytest.raises(CircuitBreakerOpenError):
                await always_fails()

            # No additional calls were made
            assert call_count == calls_after_open

    @pytest.mark.asyncio
    async def test_retry_with_cb_enabled_recovers(self):
        """After recovery timeout, the circuit allows calls again."""
        call_count = 0

        @retry_worker_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def eventually_works():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError("temp")
            return "recovered"

        with patch.object(
            app_settings.circuit_breaker, "enabled", True
        ), patch.object(
            app_settings.circuit_breaker, "failure_threshold", 2
        ), patch.object(
            app_settings.circuit_breaker, "recovery_timeout", 0.1
        ):
            # First call exhausts retries, trips circuit
            with pytest.raises(ConnectionError):
                await eventually_works()

            # Wait for recovery
            await asyncio.sleep(0.15)

            # Now the function works — circuit should allow probe
            result = await eventually_works()
            assert result == "recovered"


# ===========================================================================
# Utility tests
# ===========================================================================


class TestUtilities:
    """Test reset and registry helpers."""

    @pytest.mark.asyncio
    async def test_reset_all_circuit_breakers(self):
        cb = await get_circuit_breaker("reset_test")

        async def failing():
            raise ConnectionError()

        with pytest.raises(ConnectionError):
            await cb.call(failing)

        assert cb.failure_count > 0

        reset_all_circuit_breakers()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_open_error_attributes(self):
        err = CircuitBreakerOpenError("my_op", retry_after=5.0)
        assert err.operation_name == "my_op"
        assert err.retry_after == 5.0
        assert "my_op" in str(err)
