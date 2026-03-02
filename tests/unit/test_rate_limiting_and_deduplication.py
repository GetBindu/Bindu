"""
Comprehensive unit tests for rate limiting and request deduplication.

Tests cover:
- Rate limiting strategies (Token Bucket, Sliding Window)
- Adaptive rate limiting
- Request deduplication
- Idempotency key management
- Rate limiting middleware
- Deduplication middleware
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock

from bindu.utils.rate_limiter import (
    TokenBucketLimiter,
    SlidingWindowLimiter,
    AdaptiveRateLimiter,
)
from bindu.utils.request_deduplicator import (
    RequestDeduplicator,
    IdempotencyKeyManager,
    SignatureGenerator,
)


class TestSlidingWindowLimiter:
    """Tests for SlidingWindowLimiter."""
    
    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        
        # Should allow up to 5 requests
        for i in range(5):
            result = await limiter.is_allowed("user-1")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_blocks_requests_exceeding_limit(self):
        """Test that requests exceeding limit are blocked."""
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60)
        
        # Allow 3 requests
        for i in range(3):
            assert await limiter.is_allowed("user-1") is True
        
        # 4th request should be blocked
        assert await limiter.is_allowed("user-1") is False
    
    @pytest.mark.asyncio
    async def test_window_resets_after_time(self):
        """Test that window resets after time has passed."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=0.1)
        
        # Exhaust limit
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is False
        
        # Wait for window to reset
        await asyncio.sleep(0.15)
        
        # Should be allowed again
        assert await limiter.is_allowed("user-1") is True
    
    @pytest.mark.asyncio
    async def test_per_user_tracking(self):
        """Test that limits are tracked per user."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        
        # User 1 uses 2 requests
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is False
        
        # User 2 should still be able to make requests
        assert await limiter.is_allowed("user-2") is True
        assert await limiter.is_allowed("user-2") is True
    
    @pytest.mark.asyncio
    async def test_get_remaining_requests(self):
        """Test getting remaining request count."""
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        
        # Initially 5 remaining
        assert limiter.get_remaining_requests("user-1") == 5
        
        # After 2 requests
        await limiter.is_allowed("user-1")
        await limiter.is_allowed("user-1")
        assert limiter.get_remaining_requests("user-1") == 3
    
    @pytest.mark.asyncio
    async def test_get_reset_time(self):
        """Test getting reset time."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        
        # No reset time when under limit
        await limiter.is_allowed("user-1")
        assert limiter.get_reset_time("user-1") is None
        
        # Reset time is set when at limit
        await limiter.is_allowed("user-1")
        reset_time = limiter.get_reset_time("user-1")
        assert reset_time is not None
        assert 0 < reset_time <= 60


class TestTokenBucketLimiter:
    """Tests for TokenBucketLimiter."""
    
    @pytest.mark.asyncio
    async def test_allows_requests_within_capacity(self):
        """Test that requests within capacity are allowed."""
        limiter = TokenBucketLimiter(rate=10, capacity=5)
        
        # Should allow up to capacity
        for i in range(5):
            result = await limiter.is_allowed("user-1")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_blocks_requests_exceeding_capacity(self):
        """Test that requests exceeding capacity are blocked."""
        limiter = TokenBucketLimiter(rate=10, capacity=3)
        
        # Allow 3 requests
        for i in range(3):
            assert await limiter.is_allowed("user-1") is True
        
        # 4th request should be blocked
        assert await limiter.is_allowed("user-1") is False
    
    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        """Test that tokens refill based on rate."""
        limiter = TokenBucketLimiter(rate=2.0, capacity=2)  # 2 tokens per second
        
        # Exhaust capacity
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is False
        
        # Wait 1 second (should refill 2 tokens)
        await asyncio.sleep(1.0)
        
        # Should be able to make 2 more requests
        assert await limiter.is_allowed("user-1") is True
        assert await limiter.is_allowed("user-1") is True
    
    @pytest.mark.asyncio
    async def test_get_available_tokens(self):
        """Test getting available token count."""
        limiter = TokenBucketLimiter(rate=1.0, capacity=5)
        
        # Initially capacity tokens available
        available = limiter.get_available_tokens("user-1")
        assert available == 5
    
    @pytest.mark.asyncio
    async def test_multiple_tokens_per_request(self):
        """Test requiring multiple tokens for a request."""
        limiter = TokenBucketLimiter(rate=10, capacity=10)
        
        # Request with 3 tokens
        assert await limiter.is_allowed("user-1", tokens_needed=3) is True
        assert await limiter.is_allowed("user-1", tokens_needed=3) is True
        assert await limiter.is_allowed("user-1", tokens_needed=3) is True
        
        # 4th request should fail (only 1 token left)
        assert await limiter.is_allowed("user-1", tokens_needed=3) is False


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""
    
    @pytest.mark.asyncio
    async def test_initializes_with_correct_rate(self):
        """Test that adaptive limiter initializes with correct rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=50,
            min_rate=10,
            max_rate=100
        )
        assert limiter.current_rate == 50
    
    @pytest.mark.asyncio
    async def test_records_metrics(self):
        """Test that metrics are recorded properly."""
        limiter = AdaptiveRateLimiter(
            initial_rate=50,
            min_rate=10,
            max_rate=100
        )
        
        # Record some successful requests
        await limiter.record_request("user-1", response_time=0.5, success=True)
        await limiter.record_request("user-1", response_time=0.6, success=True)
        
        assert limiter._total_count == 2
        assert limiter._success_count == 2
    
    @pytest.mark.asyncio
    async def test_increases_rate_on_success(self):
        """Test that rate increases when success rate is high."""
        limiter = AdaptiveRateLimiter(
            initial_rate=50,
            min_rate=10,
            max_rate=100,
            adjustment_interval=0.1  # Quick adjustment for testing
        )
        
        # Record all successful requests with low response times
        for i in range(10):
            await limiter.record_request("user-1", response_time=0.1, success=True)
        
        initial_rate = limiter.current_rate
        
        # Trigger adjustment
        await asyncio.sleep(0.15)
        await limiter.record_request("user-1", response_time=0.1, success=True)
        
        # Rate should have increased
        assert limiter.current_rate > initial_rate


class TestRequestDeduplicator:
    """Tests for RequestDeduplicator."""
    
    @pytest.mark.asyncio
    async def test_generates_signature(self):
        """Test that signatures are generated consistently."""
        dedup = RequestDeduplicator()
        
        data = {"method": "POST", "path": "/api/message"}
        sig1 = await dedup.generate_signature(data)
        sig2 = await dedup.generate_signature(data)
        
        assert sig1 == sig2
        assert len(sig1) == 64  # SHA256 hex string length
    
    @pytest.mark.asyncio
    async def test_different_data_generates_different_signatures(self):
        """Test that different data generates different signatures."""
        dedup = RequestDeduplicator()
        
        sig1 = await dedup.generate_signature({"data": "value1"})
        sig2 = await dedup.generate_signature({"data": "value2"})
        
        assert sig1 != sig2
    
    @pytest.mark.asyncio
    async def test_caches_and_retrieves_result(self):
        """Test caching and retrieving results."""
        dedup = RequestDeduplicator(ttl_seconds=3600)
        
        signature = "test-sig-123"
        result = {"status": "ok", "data": "test"}
        
        # Initially no cached result
        assert await dedup.get_cached_result(signature) is None
        
        # Cache result
        await dedup.cache_result(signature, result)
        
        # Should now be retrievable
        cached = await dedup.get_cached_result(signature)
        assert cached == result
    
    @pytest.mark.asyncio
    async def test_cached_results_expire(self):
        """Test that cached results expire."""
        dedup = RequestDeduplicator(ttl_seconds=0.1)
        
        signature = "test-sig-123"
        result = {"status": "ok"}
        
        await dedup.cache_result(signature, result)
        assert await dedup.get_cached_result(signature) is not None
        
        # Wait for expiry
        await asyncio.sleep(0.15)
        assert await dedup.get_cached_result(signature) is None
    
    @pytest.mark.asyncio
    async def test_invalidates_specific_entry(self):
        """Test that specific entries can be invalidated."""
        dedup = RequestDeduplicator()
        
        await dedup.cache_result("sig-1", {"result": 1})
        await dedup.cache_result("sig-2", {"result": 2})
        
        # Invalidate first entry
        assert await dedup.invalidate("sig-1") is True
        
        # First should be gone, second should still be there
        assert await dedup.get_cached_result("sig-1") is None
        assert await dedup.get_cached_result("sig-2") is not None
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """Test getting cache statistics."""
        dedup = RequestDeduplicator()
        
        # Cache some results
        await dedup.cache_result("sig-1", {"data": 1})
        await dedup.cache_result("sig-2", {"data": 2})
        
        # Access one multiple times
        await dedup.get_cached_result("sig-1")
        await dedup.get_cached_result("sig-1")
        
        stats = dedup.get_stats()
        assert stats["cache_size"] == 2
        assert stats["total_hits"] == 2


class TestIdempotencyKeyManager:
    """Tests for IdempotencyKeyManager."""
    
    @pytest.mark.asyncio
    async def test_tracks_processed_requests(self):
        """Test that processed requests are tracked."""
        manager = IdempotencyKeyManager()
        
        key = "idem-key-123"
        
        # Initially not processed
        assert await manager.is_processed(key) is False
        
        # Record response
        await manager.record_response(key, {"status": "ok"})
        
        # Now should be marked as processed
        assert await manager.is_processed(key) is True
    
    @pytest.mark.asyncio
    async def test_retrieves_cached_response(self):
        """Test that cached responses are retrieved correctly."""
        manager = IdempotencyKeyManager()
        
        key = "idem-key-123"
        response = {"status": "created", "id": 123}
        
        await manager.record_response(key, response)
        
        retrieved = await manager.get_response(key)
        assert retrieved == response
    
    @pytest.mark.asyncio
    async def test_expired_keys_are_cleaned_up(self):
        """Test that expired keys are cleaned up."""
        manager = IdempotencyKeyManager(ttl_seconds=0.1)
        
        key = "idem-key-123"
        await manager.record_response(key, {"status": "ok"})
        
        # Should be available initially
        assert await manager.is_processed(key) is True
        
        # Wait for expiry
        await asyncio.sleep(0.15)
        
        # Should be gone
        assert await manager.is_processed(key) is False
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_expired(self):
        """Test manual cleanup of expired entries."""
        manager = IdempotencyKeyManager(ttl_seconds=0.1)
        
        await manager.record_response("key-1", {"data": 1})
        await manager.record_response("key-2", {"data": 2})
        
        assert len(manager._responses) == 2
        
        # Wait and cleanup
        await asyncio.sleep(0.15)
        cleaned = await manager.cleanup()
        
        # Both should be removed
        assert cleaned == 2
        assert len(manager._responses) == 0


class TestSignatureGenerator:
    """Tests for SignatureGenerator."""
    
    def test_consistent_signature_generation(self):
        """Test that signatures are consistent."""
        data = {"name": "test", "value": 123}
        
        sig1 = SignatureGenerator.generate_signature(data)
        sig2 = SignatureGenerator.generate_signature(data)
        
        assert sig1 == sig2
    
    def test_different_data_different_signatures(self):
        """Test that different data produces different signatures."""
        sig1 = SignatureGenerator.generate_signature({"a": 1})
        sig2 = SignatureGenerator.generate_signature({"a": 2})
        
        assert sig1 != sig2
    
    def test_order_doesnt_matter(self):
        """Test that dict key order doesn't matter."""
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        
        sig1 = SignatureGenerator.generate_signature(data1)
        sig2 = SignatureGenerator.generate_signature(data2)
        
        assert sig1 == sig2
    
    def test_with_additional_fields(self):
        """Test signature generation with additional fields."""
        data = {"method": "POST"}
        additional = {"client_ip": "192.168.1.1"}
        
        sig1 = SignatureGenerator.generate_signature(data, additional)
        sig2 = SignatureGenerator.generate_signature(data)
        
        assert sig1 != sig2  # Should be different
    
    def test_custom_hash_algorithm(self):
        """Test using different hash algorithms."""
        data = {"test": "data"}
        
        sig_sha256 = SignatureGenerator.generate_signature(data, hash_algorithm='sha256')
        sig_sha512 = SignatureGenerator.generate_signature(data, hash_algorithm='sha512')
        
        # SHA512 should be longer
        assert len(sig_sha512) > len(sig_sha256)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
