"""
Advanced rate limiting utilities for Bindu agents.

Provides multiple rate limiting strategies:
- Token Bucket: Smooth, uses tokens that refill over time
- Sliding Window: Precise request counting over a time window
- Per-agent limiting: Separate limits for each agent

Usage:
    from bindu.utils.rate_limiter import TokenBucketLimiter, SlidingWindowLimiter
    
    # Token bucket strategy
    limiter = TokenBucketLimiter(rate=100, capacity=100)
    if limiter.is_allowed("agent-123"):
        # Process request
        pass
    
    # Sliding window strategy
    limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)
    if limiter.is_allowed("agent-456"):
        # Process request
        pass
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    max_requests: int
    """Maximum number of requests allowed"""
    
    window_seconds: float
    """Time window in seconds"""
    
    per_agent: bool = True
    """Whether to apply limits per agent/user"""
    
    burst_size: Optional[int] = None
    """Maximum burst size (for token bucket)"""
    
    cleanup_interval: float = 60.0
    """Interval in seconds to clean up old entries"""


class RateLimiter(ABC):
    """Abstract base class for rate limiting strategies."""
    
    def __init__(self, max_requests: int, window_seconds: float):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._identifiers: Dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._lock = asyncio.Lock()
        
    @abstractmethod
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed.
        
        Args:
            identifier: Unique identifier (agent ID, user ID, etc.)
            
        Returns:
            True if request is allowed, False otherwise
        """
        pass
    
    async def _cleanup_old_entries(self) -> None:
        """Remove old entries from tracking dictionary."""
        current_time = time.time()
        # Cleanup every minute to avoid memory leaks
        if current_time - self._last_cleanup < 60:
            return
            
        cutoff_time = current_time - (self.window_seconds * 2)
        identifiers_to_check = list(self._identifiers.keys())
        
        for identifier in identifiers_to_check:
            timestamps = self._identifiers[identifier]
            # Keep only recent timestamps
            self._identifiers[identifier] = [
                ts for ts in timestamps if ts > cutoff_time
            ]
            # Remove identifier if no recent requests
            if not self._identifiers[identifier]:
                del self._identifiers[identifier]
        
        self._last_cleanup = current_time


class SlidingWindowLimiter(RateLimiter):
    """
    Sliding Window Rate Limiter.
    
    Uses a precise timestamp-based approach. Counts requests in a sliding
    time window. More accurate than fixed windows but uses more memory.
    
    Example:
        limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)
        if await limiter.is_allowed("user-123"):
            # Process request
            pass
    """
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed using sliding window.
        
        Args:
            identifier: Unique identifier for rate limit tracking
            
        Returns:
            True if within rate limit, False otherwise
        """
        async with self._lock:
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Get timestamps for this identifier
            timestamps = self._identifiers[identifier]
            
            # Remove old timestamps outside the window
            timestamps = [ts for ts in timestamps if ts > window_start]
            self._identifiers[identifier] = timestamps
            
            # Check if we're under the limit
            if len(timestamps) < self.max_requests:
                timestamps.append(current_time)
                return True
            
            # Cleanup old entries periodically
            await self._cleanup_old_entries()
            
            return False
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier in current window.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Number of requests still allowed
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        timestamps = self._identifiers.get(identifier, [])
        recent_timestamps = [ts for ts in timestamps if ts > window_start]
        
        return max(0, self.max_requests - len(recent_timestamps))
    
    def get_reset_time(self, identifier: str) -> Optional[float]:
        """Get time in seconds until next requests are allowed.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Seconds until rate limit resets, or None if no limit active
        """
        timestamps = self._identifiers.get(identifier, [])
        if not timestamps or len(timestamps) < self.max_requests:
            return None
        
        oldest_timestamp = min(timestamps)
        reset_time = oldest_timestamp + self.window_seconds - time.time()
        return max(0, reset_time)


class TokenBucketLimiter(RateLimiter):
    """
    Token Bucket Rate Limiter.
    
    Allows smooth traffic with burst capacity. Tokens refill at a constant
    rate. Useful for smoothing traffic spikes while maintaining average rate.
    
    Example:
        limiter = TokenBucketLimiter(rate=100, capacity=100)
        if await limiter.is_allowed("user-123"):
            # Process request
            pass
    """
    
    @dataclass
    class Bucket:
        """Bucket state for a specific identifier."""
        tokens: float
        """Current tokens in bucket"""
        
        last_refill: float
        """Timestamp of last refill"""
    
    def __init__(
        self,
        rate: float,
        capacity: float,
        window_seconds: float = 1.0
    ):
        """Initialize token bucket limiter.
        
        Args:
            rate: Tokens per second (e.g., 100 = 100 tokens/sec)
            capacity: Maximum tokens in bucket (burst size)
            window_seconds: Not used, kept for compatibility
        """
        self.rate = rate
        self.capacity = capacity
        self._buckets: Dict[str, self.Bucket] = {}
        self._last_cleanup = time.time()
        self._lock = asyncio.Lock()
    
    async def _refill_bucket(self, identifier: str) -> TokenBucketLimiter.Bucket:
        """Refill bucket based on elapsed time.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Updated bucket
        """
        current_time = time.time()
        
        if identifier not in self._buckets:
            bucket = self.Bucket(tokens=self.capacity, last_refill=current_time)
            self._buckets[identifier] = bucket
            return bucket
        
        bucket = self._buckets[identifier]
        elapsed = current_time - bucket.last_refill
        
        # Add tokens based on elapsed time
        new_tokens = bucket.tokens + (elapsed * self.rate)
        bucket.tokens = min(new_tokens, self.capacity)
        bucket.last_refill = current_time
        
        return bucket
    
    async def is_allowed(
        self,
        identifier: str,
        tokens_needed: float = 1.0
    ) -> bool:
        """Check if request is allowed using token bucket.
        
        Args:
            identifier: Unique identifier for rate limit tracking
            tokens_needed: Number of tokens required (default: 1)
            
        Returns:
            True if tokens available, False otherwise
        """
        async with self._lock:
            bucket = await self._refill_bucket(identifier)
            
            if bucket.tokens >= tokens_needed:
                bucket.tokens -= tokens_needed
                return True
            
            # Cleanup old entries periodically
            current_time = time.time()
            if current_time - self._last_cleanup > 60:
                await self._cleanup_old_entries()
            
            return False
    
    def get_available_tokens(self, identifier: str) -> float:
        """Get current available tokens for identifier.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Number of available tokens
        """
        if identifier not in self._buckets:
            return self.capacity
        
        bucket = self._buckets[identifier]
        current_time = time.time()
        elapsed = current_time - bucket.last_refill
        
        available = min(
            bucket.tokens + (elapsed * self.rate),
            self.capacity
        )
        return available
    
    async def _cleanup_old_entries(self) -> None:
        """Remove unused buckets to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - 3600  # Remove buckets unused for 1 hour
        
        identifiers_to_remove = [
            id for id, bucket in self._buckets.items()
            if bucket.last_refill < cutoff_time
        ]
        
        for identifier in identifiers_to_remove:
            del self._buckets[identifier]
        
        self._last_cleanup = current_time


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts limits based on system load.
    
    Monitors response times and success rates, automatically adjusting
    the allowed request rate to optimize throughput.
    """
    
    def __init__(
        self,
        initial_rate: int,
        min_rate: int,
        max_rate: int,
        adjustment_interval: float = 30.0
    ):
        """Initialize adaptive limiter.
        
        Args:
            initial_rate: Starting rate limit
            min_rate: Minimum allowed rate
            max_rate: Maximum allowed rate
            adjustment_interval: Interval in seconds between adjustments
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adjustment_interval = adjustment_interval
        self._last_adjustment = time.time()
        self._response_times: list[float] = []
        self._success_count = 0
        self._total_count = 0
        self._limiter = TokenBucketLimiter(
            rate=initial_rate,
            capacity=initial_rate
        )
        self._lock = asyncio.Lock()
    
    async def record_request(
        self,
        identifier: str,
        response_time: float,
        success: bool
    ) -> None:
        """Record metrics for adaptive adjustment.
        
        Args:
            identifier: Request identifier
            response_time: Request processing time in seconds
            success: Whether request was successful
        """
        async with self._lock:
            self._response_times.append(response_time)
            self._total_count += 1
            if success:
                self._success_count += 1
            
            # Adjust rate if interval has passed
            current_time = time.time()
            if current_time - self._last_adjustment >= self.adjustment_interval:
                await self._adjust_rate()
    
    async def _adjust_rate(self) -> None:
        """Adjust rate based on collected metrics."""
        if self._total_count == 0:
            return
        
        success_rate = self._success_count / self._total_count
        avg_response_time = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times else 0
        )
        
        # Increase rate if success rate is high and response time is low
        if success_rate > 0.95 and avg_response_time < 1.0:
            self.current_rate = min(self.current_rate + 10, self.max_rate)
        # Decrease rate if success rate is low or response time is high
        elif success_rate < 0.90 or avg_response_time > 2.0:
            self.current_rate = max(self.current_rate - 10, self.min_rate)
        
        # Update limiter with new rate
        self._limiter.rate = self.current_rate
        self._limiter.capacity = self.current_rate
        
        # Reset metrics
        self._response_times.clear()
        self._success_count = 0
        self._total_count = 0
        self._last_adjustment = time.time()
        
        logger.info(f"Adjusted rate limit to {self.current_rate}/s")
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            True if allowed, False otherwise
        """
        return await self._limiter.is_allowed(identifier)
