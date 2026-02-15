"""Tests for circuit breaker implementation."""

import asyncio
import pytest
from bindu.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    CircuitBreakerRegistry,
)


class MockException(Exception):
    """Mock exception for testing."""
    pass


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state():
    """Test circuit breaker in closed state allows requests."""
    breaker = CircuitBreaker(failure_threshold=3, name="test")
    
    assert breaker.is_closed
    assert not breaker.is_open
    
    # Successful requests should work
    async with breaker:
        pass
    
    assert breaker.metrics.successful_requests == 1
    assert breaker.is_closed


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test circuit breaker opens after threshold failures."""
    breaker = CircuitBreaker(
        failure_threshold=3,
        expected_exception=MockException,
        name="test_failures"
    )
    
    # Cause failures
    for _ in range(3):
        try:
            async with breaker:
                raise MockException("Test failure")
        except MockException:
            pass
    
    # Circuit should be open
    assert breaker.is_open
    assert breaker.metrics.failed_requests == 3


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test circuit breaker rejects requests when open."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10,
        expected_exception=MockException,
        name="test_open"
    )
    
    # Open the circuit
    for _ in range(2):
        try:
            async with breaker:
                raise MockException("Test failure")
        except MockException:
            pass
    
    assert breaker.is_open
    
    # Next request should be rejected
    with pytest.raises(CircuitBreakerOpenError):
        async with breaker:
            pass
    
    assert breaker.metrics.rejected_requests == 1


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker transitions to half-open and recovers."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=0.1,  # Very short for testing
        success_threshold=2,
        expected_exception=MockException,
        name="test_recovery"
    )
    
    # Open the circuit
    for _ in range(2):
        try:
            async with breaker:
                raise MockException("Test failure")
        except MockException:
            pass
    
    assert breaker.is_open
    
    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    
    # Next request should be allowed (half-open)
    async with breaker:
        pass
    
    assert breaker.is_half_open
    
    # One more success should close it
    async with breaker:
        pass
    
    assert breaker.is_closed
    assert breaker.metrics.state_transitions["half_open_to_closed"] == 1


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_open():
    """Test circuit breaker returns to open if failure in half-open."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=0.1,
        expected_exception=MockException,
        name="test_half_open_fail"
    )
    
    # Open the circuit
    for _ in range(2):
        try:
            async with breaker:
                raise MockException("Test failure")
        except MockException:
            pass
    
    # Wait for recovery
    await asyncio.sleep(0.15)
    
    # Fail in half-open state
    try:
        async with breaker:
            raise MockException("Test failure")
    except MockException:
        pass
    
    # Should be open again
    assert breaker.is_open
    assert breaker.metrics.state_transitions["half_open_to_open"] == 1


@pytest.mark.asyncio
async def test_circuit_breaker_metrics():
    """Test circuit breaker tracks metrics correctly."""
    breaker = CircuitBreaker(failure_threshold=5, name="test_metrics")
    
    # Some successes
    for _ in range(3):
        async with breaker:
            pass
    
    # Some failures
    for _ in range(2):
        try:
            async with breaker:
                raise Exception("Test failure")
        except Exception:
            pass
    
    metrics = breaker.metrics
    assert metrics.successful_requests == 3
    assert metrics.failed_requests == 2
    assert metrics.total_requests == 5
    assert metrics.success_rate() == 60.0


@pytest.mark.asyncio
async def test_circuit_breaker_registry():
    """Test circuit breaker registry management."""
    registry = CircuitBreakerRegistry()
    
    # Create breakers
    breaker1 = registry.get_or_create("agent_1", failure_threshold=3)
    breaker2 = registry.get_or_create("agent_2", failure_threshold=5)
    
    assert registry.get("agent_1") == breaker1
    assert registry.get("agent_2") == breaker2
    
    # Open one circuit
    await breaker1.force_open()
    
    open_circuits = registry.get_open_circuits()
    assert "agent_1" in open_circuits
    assert "agent_2" not in open_circuits


@pytest.mark.asyncio
async def test_circuit_breaker_force_operations():
    """Test manual circuit breaker control."""
    breaker = CircuitBreaker(failure_threshold=5, name="test_force")
    
    # Force open
    await breaker.force_open()
    assert breaker.is_open
    
    # Should reject requests
    with pytest.raises(CircuitBreakerOpenError):
        async with breaker:
            pass
    
    # Force close
    await breaker.force_close()
    assert breaker.is_closed
    
    # Should allow requests
    async with breaker:
        pass


@pytest.mark.asyncio
async def test_circuit_breaker_status():
    """Test circuit breaker status reporting."""
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=60,
        name="test_status"
    )
    
    # Generate some activity
    async with breaker:
        pass
    
    try:
        async with breaker:
            raise Exception("Test")
    except Exception:
        pass
    
    status = breaker.get_status()
    
    assert status["name"] == "test_status"
    assert status["state"] == "closed"
    assert status["config"]["failure_threshold"] == 3
    assert status["metrics"]["total_requests"] == 2
    assert "recent_failures" in status


@pytest.mark.asyncio
async def test_circuit_breaker_concurrent_requests():
    """Test circuit breaker handles concurrent requests correctly."""
    breaker = CircuitBreaker(
        failure_threshold=5,
        half_open_max_calls=2,
        name="test_concurrent"
    )
    
    # Create concurrent successful requests
    tasks = [breaker.__aenter__() for _ in range(10)]
    await asyncio.gather(*tasks)
    
    # All should succeed in closed state
    assert breaker.metrics.successful_requests == 0  # Not exited yet
    
    # Exit all contexts
    for _ in range(10):
        await breaker.__aexit__(None, None, None)
    
    assert breaker.metrics.successful_requests == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
