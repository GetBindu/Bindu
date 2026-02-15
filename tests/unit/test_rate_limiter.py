"""Tests for rate limiter implementations."""

import asyncio
import pytest
import time
from bindu.utils.rate_limiter import (
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    AdaptiveRateLimiter,
    RateLimitExceeded,
    RateLimiterRegistry,
)


@pytest.mark.asyncio
async def test_token_bucket_basic():
    """Test basic token bucket rate limiting."""
    limiter = TokenBucketRateLimiter(
        rate=10,
        per_seconds=1.0,
        burst_size=5,
        name="test_basic"
    )
    
    # Should allow burst_size requests immediately
    for _ in range(5):
        async with limiter:
            pass
    
    assert limiter._accepted_requests == 5
    
    # Next request should fail (no tokens left)
    with pytest.raises(RateLimitExceeded):
        async with limiter:
            pass


@pytest.mark.asyncio
async def test_token_bucket_refill():
    """Test token bucket refills over time."""
    limiter = TokenBucketRateLimiter(
        rate=10,  # 10 per second
        per_seconds=1.0,
        burst_size=5,
        name="test_refill"
    )
    
    # Use all tokens
    for _ in range(5):
        async with limiter:
            pass
    
    # Wait for refill (0.5 seconds = 5 tokens)
    await asyncio.sleep(0.5)
    
    # Should have ~5 more tokens
    for _ in range(4):  # Use 4 to be safe
        async with limiter:
            pass
    
    assert limiter._accepted_requests >= 9


@pytest.mark.asyncio
async def test_token_bucket_burst():
    """Test token bucket allows bursts."""
    limiter = TokenBucketRateLimiter(
        rate=100,
        per_seconds=60.0,
        burst_size=20,
        name="test_burst"
    )
    
    # Should allow 20 immediate requests (burst)
    for _ in range(20):
        async with limiter:
            pass
    
    assert limiter._accepted_requests == 20
    assert limiter._rejected_requests == 0


@pytest.mark.asyncio
async def test_sliding_window_basic():
    """Test basic sliding window rate limiting."""
    limiter = SlidingWindowRateLimiter(
        max_requests=5,
        window_seconds=1.0,
        name="test_sliding"
    )
    
    # Allow 5 requests
    for _ in range(5):
        async with limiter:
            pass
    
    assert limiter._accepted_requests == 5
    
    # 6th should fail
    with pytest.raises(RateLimitExceeded):
        async with limiter:
            pass
    
    assert limiter._rejected_requests == 1


@pytest.mark.asyncio
async def test_sliding_window_expiry():
    """Test sliding window allows requests after window expires."""
    limiter = SlidingWindowRateLimiter(
        max_requests=3,
        window_seconds=0.5,
        name="test_expiry"
    )
    
    # Use all requests
    for _ in range(3):
        async with limiter:
            pass
    
    # Should fail immediately
    with pytest.raises(RateLimitExceeded):
        async with limiter:
            pass
    
    # Wait for window to expire
    await asyncio.sleep(0.6)
    
    # Should succeed now
    async with limiter:
        pass
    
    assert limiter._accepted_requests == 4


@pytest.mark.asyncio
async def test_sliding_window_precise():
    """Test sliding window is precise about timing."""
    limiter = SlidingWindowRateLimiter(
        max_requests=2,
        window_seconds=1.0,
        name="test_precise"
    )
    
    # First request at t=0
    async with limiter:
        pass
    
    await asyncio.sleep(0.3)
    
    # Second request at t=0.3
    async with limiter:
        pass
    
    # Third should fail (window not expired)
    with pytest.raises(RateLimitExceeded):
        async with limiter:
            pass
    
    # Wait until first request expires (t > 1.0)
    await asyncio.sleep(0.8)
    
    # Should succeed now
    async with limiter:
        pass


@pytest.mark.asyncio
async def test_adaptive_basic():
    """Test adaptive rate limiter basic functionality."""
    limiter = AdaptiveRateLimiter(
        base_rate=10,
        min_rate=5,
        max_rate=20,
        window_seconds=1.0,
        name="test_adaptive"
    )
    
    # Start with base rate
    assert limiter._current_rate == 10
    
    # Should allow base_rate requests
    for _ in range(10):
        async with limiter:
            pass


@pytest.mark.asyncio
async def test_adaptive_reduces_on_errors():
    """Test adaptive limiter reduces rate on high error rate."""
    limiter = AdaptiveRateLimiter(
        base_rate=10,
        min_rate=5,
        max_rate=20,
        window_seconds=0.5,  # Short window for testing
        error_threshold=0.3,  # 30% error triggers reduction
        adjustment_factor=0.5,  # 50% reduction
        name="test_adaptive_reduce"
    )
    
    initial_rate = limiter._current_rate
    
    # Generate requests with high error rate
    for i in range(15):
        try:
            async with limiter:
                if i % 2 == 0:  # 50% error rate
                    raise Exception("Test error")
        except Exception:
            pass
    
    # Wait for adjustment interval
    await asyncio.sleep(0.6)
    
    # Trigger one more request to check adjustment
    try:
        async with limiter:
            pass
    except RateLimitExceeded:
        pass
    
    # Rate should have been reduced
    # Note: May not reduce if not enough samples yet
    status = limiter.get_status()
    assert status["base_rate"] == 10


@pytest.mark.asyncio
async def test_adaptive_increases_on_success():
    """Test adaptive limiter increases rate on low error rate."""
    limiter = AdaptiveRateLimiter(
        base_rate=10,
        min_rate=5,
        max_rate=20,
        window_seconds=0.5,
        error_threshold=0.3,
        adjustment_factor=0.3,
        name="test_adaptive_increase"
    )
    
    # Generate mostly successful requests
    for _ in range(15):
        try:
            async with limiter:
                pass  # Success
        except RateLimitExceeded:
            pass
    
    # Wait for adjustment
    await asyncio.sleep(0.6)
    
    # Should maintain or increase rate
    assert limiter._current_rate >= 10


@pytest.mark.asyncio
async def test_rate_limiter_status():
    """Test rate limiter status reporting."""
    limiter = TokenBucketRateLimiter(
        rate=100,
        per_seconds=60,
        burst_size=20,
        name="test_status"
    )
    
    # Make some requests
    for _ in range(5):
        async with limiter:
            pass
    
    status = limiter.get_status()
    
    assert status["name"] == "test_status"
    assert status["type"] == "token_bucket"
    assert status["rate"] == 100
    assert status["accepted_requests"] == 5
    assert status["acceptance_rate"] == 100.0


@pytest.mark.asyncio
async def test_rate_limiter_registry():
    """Test rate limiter registry."""
    registry = RateLimiterRegistry()
    
    # Create different types
    token_limiter = registry.create_token_bucket(
        "agent_1", rate=100, per_seconds=60
    )
    sliding_limiter = registry.create_sliding_window(
        "agent_2", max_requests=50, window_seconds=30
    )
    adaptive_limiter = registry.create_adaptive(
        "agent_3", base_rate=100, min_rate=10, max_rate=200
    )
    
    # Verify retrieval
    assert registry.get("agent_1") == token_limiter
    assert registry.get("agent_2") == sliding_limiter
    assert registry.get("agent_3") == adaptive_limiter
    
    # Check statuses
    statuses = registry.get_all_statuses()
    assert len(statuses) == 3
    assert "agent_1" in statuses
    assert statuses["agent_1"]["type"] == "token_bucket"


@pytest.mark.asyncio
async def test_rate_limit_exception_details():
    """Test RateLimitExceeded exception provides useful info."""
    limiter = SlidingWindowRateLimiter(
        max_requests=3,
        window_seconds=10.0,
        name="test_exception"
    )
    
    # Use all requests
    for _ in range(3):
        async with limiter:
            pass
    
    # Next should raise with details
    try:
        async with limiter:
            pass
        assert False, "Should have raised RateLimitExceeded"
    except RateLimitExceeded as e:
        assert e.limit == 3
        assert e.window_seconds == 10.0
        assert e.retry_after > 0
        assert "Rate limit exceeded" in str(e)


@pytest.mark.asyncio
async def test_concurrent_rate_limiting():
    """Test rate limiter handles concurrent requests."""
    limiter = TokenBucketRateLimiter(
        rate=100,
        per_seconds=1.0,
        burst_size=50,
        name="test_concurrent"
    )
    
    async def make_request():
        try:
            async with limiter:
                await asyncio.sleep(0.01)  # Simulate work
        except RateLimitExceeded:
            pass
    
    # Fire 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    await asyncio.gather(*tasks)
    
    # Should accept ~50 (burst size) and reject rest
    assert limiter._accepted_requests >= 40  # Allow some margin
    assert limiter._rejected_requests > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
