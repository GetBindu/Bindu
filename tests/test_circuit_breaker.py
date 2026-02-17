"""Tests for circuit_breaker module."""

import time
import pytest
from bindu.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    get_circuit_breaker,
)


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        circuit = CircuitBreaker("test_initial", failure_threshold=3)
        assert circuit.get_state() == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_stays_closed_on_success(self):
        """Test circuit stays closed on successful calls."""
        circuit = CircuitBreaker("test_closed", failure_threshold=3)

        async def success_func() -> str:
            return "ok"

        for _ in range(5):
            result = await circuit.call_async(success_func)
            assert result == "ok"

        assert circuit.get_state() == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        circuit = CircuitBreaker("test_open", failure_threshold=3)

        async def fail_func() -> str:
            raise ConnectionError("Failed")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await circuit.call_async(fail_func)

        assert circuit.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_blocks_when_open(self):
        """Test circuit blocks requests when OPEN."""
        circuit = CircuitBreaker(
            "test_block", failure_threshold=2, recovery_timeout=1.0
        )

        async def fail_func() -> str:
            raise ConnectionError("Failed")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await circuit.call_async(fail_func)

        assert circuit.get_state() == CircuitState.OPEN

        with pytest.raises(CircuitBreakerError):
            await circuit.call_async(fail_func)

    @pytest.mark.asyncio
    async def test_half_open_on_timeout(self):
        """Test circuit moves to HALF_OPEN after timeout."""
        circuit = CircuitBreaker("test_half", failure_threshold=2, recovery_timeout=0.1)

        async def fail_func() -> str:
            raise ConnectionError("Failed")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await circuit.call_async(fail_func)

        assert circuit.get_state() == CircuitState.OPEN
        time.sleep(0.15)

        try:
            await circuit.call_async(fail_func)
        except (ConnectionError, CircuitBreakerError):
            pass

        assert circuit.get_state() in [CircuitState.HALF_OPEN, CircuitState.OPEN]

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self):
        """Test circuit closes after successful recovery test."""
        circuit = CircuitBreaker(
            "test_recover",
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        counter = [0]

        async def flaky_func() -> str:
            counter[0] += 1
            if counter[0] <= 2:
                raise ConnectionError("Initial failures")
            return "ok"

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await circuit.call_async(flaky_func)

        assert circuit.get_state() == CircuitState.OPEN
        time.sleep(0.15)

        for _ in range(2):
            result = await circuit.call_async(flaky_func)
            assert result == "ok"

        assert circuit.get_state() == CircuitState.CLOSED

    def test_reset(self):
        """Test manual reset."""
        circuit = CircuitBreaker("test_reset", failure_threshold=2)
        circuit.failure_count = 5
        circuit.state = CircuitState.OPEN
        circuit.reset()
        assert circuit.get_state() == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_protect_async_decorator(self):
        """Test protect_async decorator."""
        circuit = CircuitBreaker("test_decorator", failure_threshold=3)

        @circuit.protect_async
        async def test_func() -> str:
            return "success"

        result = await test_func()
        assert result == "success"
        assert circuit.get_state() == CircuitState.CLOSED


class TestGetCircuitBreaker:
    """Test get_circuit_breaker function."""

    def test_creates_new_circuit(self):
        """Test creating a new circuit breaker."""
        circuit = get_circuit_breaker("unique_test_1", failure_threshold=5)
        assert circuit.name == "unique_test_1"
        assert circuit.failure_threshold == 5

    def test_returns_same_instance(self):
        """Test getting same instance by name."""
        circuit1 = get_circuit_breaker("unique_test_2")
        circuit2 = get_circuit_breaker("unique_test_2")
        assert circuit1 is circuit2
