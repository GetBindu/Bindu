# Advanced Request Rate Limiting & Deduplication System

## Overview

This comprehensive system provides production-ready rate limiting, request deduplication, and idempotency handling for AI agents in Bindu. It prevents resource exhaustion, handles duplicate requests, and ensures fair resource allocation across agents.

## Features

###  Rate Limiting Strategies

- **Sliding Window**: Precise timestamp-based counting over a time window
- **Token Bucket**: Smooth traffic with burst capacity, tokens refill over time
- **Adaptive**: Automatically adjusts limits based on system load and response times

### Request Deduplication

- Cache request signatures and results
- Handle retries gracefully with cached responses
- Automatic cache cleanup and memory management
- Per-request TTL configuration

###  Idempotency Support

- Idempotency-Key header support
- Automatic response caching for idempotent operations
- Safe retry handling with guaranteed result consistency

## Quick Start

### 1. Basic Rate Limiting

```python
from bindu.server.applications import BinduApplication
from bindu.server.middleware.rate_limit import RateLimitMiddleware
from bindu.utils.rate_limiter import SlidingWindowLimiter
from starlette.middleware import Middleware

# Create rate limiter: 100 requests per 60 seconds
limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)

# Create middleware
middleware = [
    Middleware(
        RateLimitMiddleware,
        limiter=limiter,
        identifier_header="X-Agent-ID",
    )
]

# Use in application
app = BinduApplication(
    manifest=your_manifest,
    middleware=middleware,
)
```

### 2. Token Bucket Rate Limiting

Allows smooth traffic with controlled bursts:

```python
from bindu.utils.rate_limiter import TokenBucketLimiter

# 100 tokens per second, max 200 burst
limiter = TokenBucketLimiter(rate=100, capacity=200)

# Check if request is allowed
if await limiter.is_allowed("agent-123"):
    # Process request
    pass

# Require multiple tokens for expensive operations
if await limiter.is_allowed("agent-456", tokens_needed=5):
    # Process expensive operation
    pass
```

### 3. Request Deduplication

```python
from bindu.server.middleware.rate_limit import RequestDeduplicationMiddleware
from bindu.utils.request_deduplicator import RequestDeduplicator

# Create deduplicator with 1-hour TTL
dedup = RequestDeduplicator(ttl_seconds=3600)

# Add to middleware
middleware = [
    Middleware(
        RequestDeduplicationMiddleware,
        deduplicator=dedup,
        request_methods=["GET", "HEAD"],
        cache_ttl=3600,
    )
]

# Manual usage
signature = await dedup.generate_signature(request_data)
cached_result = await dedup.get_cached_result(signature)

if not cached_result:
    result = await process_request()
    await dedup.cache_result(signature, result)
```

### 4. Idempotent Operations

```python
from bindu.server.middleware.rate_limit import IdempotencyMiddleware
from bindu.utils.request_deduplicator import IdempotencyKeyManager

# Create manager
manager = IdempotencyKeyManager(ttl_seconds=86400)  # 24 hours

# Add to middleware
middleware = [
    Middleware(
        IdempotencyMiddleware,
        key_manager=manager,
        key_header="Idempotency-Key",
    )
]
```

Client usage:
```bash
curl -X POST http://localhost:3773/api/payment \
  -H "Idempotency-Key: payment-123" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'

# Repeat request with same Idempotency-Key
# Will get same response without reprocessing
curl -X POST http://localhost:3773/api/payment \
  -H "Idempotency-Key: payment-123" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'
```

### 5. Adaptive Rate Limiting

Automatically adjusts limits based on system performance:

```python
from bindu.utils.rate_limiter import AdaptiveRateLimiter

# Start at 50 req/s, range 10-100 req/s, adjust every 30 seconds
adapter = AdaptiveRateLimiter(
    initial_rate=50,
    min_rate=10,
    max_rate=100,
    adjustment_interval=30.0,
)

# Check if allowed
if await adapter.is_allowed("agent-456"):
    # Process request
    pass

# Record metrics for adaptation
await adapter.record_request(
    identifier="agent-456",
    response_time=0.5,
    success=True,
)
```

## Response Headers

### Rate Limit Headers
```
X-RateLimit-Remaining: 95    # Requests remaining in window
X-RateLimit-Reset: 32        # Seconds until limit resets
```

### Cache Headers
```
X-Cache-Hit: true            # Response was from cache
X-Idempotent-Cached: false   # Idempotent key was cached
Idempotency-Key: key-123     # Echo back the idempotency key
```

## Configuration Examples

### Per-Endpoint Rate Limits

```python
from bindu.server.middleware.rate_limit import RateLimitMiddleware
from bindu.utils.rate_limiter import SlidingWindowLimiter
from starlette.middleware import Middleware

# Strict limit for expensive operations
limiter_strict = SlidingWindowLimiter(max_requests=10, window_seconds=60)

# Relaxed limit for normal operations
limiter_normal = SlidingWindowLimiter(max_requests=1000, window_seconds=60)

# Apply to expensive endpoints
expensive_middleware = Middleware(
    RateLimitMiddleware,
    limiter=limiter_strict,
)

# Apply to normal endpoints
normal_middleware = Middleware(
    RateLimitMiddleware,
    limiter=limiter_normal,
    excluded_paths=["/health", "/metrics"],
)
```

### By-Agent Rate Limiting

```python
# Rate limiter uses X-Agent-ID header by default
# Each agent gets their own limit

limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)

# agent-1 gets 100 req/min
# agent-2 gets 100 req/min
# agent-3 gets 100 req/min
# (separate buckets for each)
```

### Custom Identifier Extraction

```python
from bindu.server.middleware.rate_limit import RateLimitMiddleware

middleware = Middleware(
    RateLimitMiddleware,
    limiter=limiter,
    identifier_header="X-Organization-ID",  # Use org ID instead
)
```

## Advanced Usage

### Cache Statistics

```python
dedup = RequestDeduplicator()

# Get cache metrics
stats = dedup.get_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Total hits: {stats['total_hits']}")
print(f"Average hits per entry: {stats['average_hits_per_entry']}")
```

### Manual Cache Management

```python
# Invalidate specific entry
success = await dedup.invalidate("request-sig-123")

# Clear entire cache
count = await dedup.clear_all()
print(f"Cleared {count} entries")
```

### Sliding Window Utilities

```python
limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)

# Check remaining requests
remaining = limiter.get_remaining_requests("agent-123")
print(f"Remaining requests: {remaining}")

# Get time until reset
reset_time = limiter.get_reset_time("agent-123")
if reset_time:
    print(f"Rate limit resets in {reset_time:.1f} seconds")
```

### Token Bucket Utilities

```python
limiter = TokenBucketLimiter(rate=100, capacity=200)

# Check available tokens
available = limiter.get_available_tokens("agent-123")
print(f"Available tokens: {available:.1f}")
```

## Complete Application Example

```python
from bindu.server.applications import BinduApplication
from bindu.server.middleware.rate_limit import (
    RateLimitMiddleware,
    RequestDeduplicationMiddleware,
    IdempotencyMiddleware,
)
from bindu.utils.rate_limiter import SlidingWindowLimiter, TokenBucketLimiter
from bindu.utils.request_deduplicator import RequestDeduplicator, IdempotencyKeyManager
from starlette.middleware import Middleware

# Create limiters
rate_limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)
deduplicator = RequestDeduplicator(ttl_seconds=3600)
idempotency_manager = IdempotencyKeyManager(ttl_seconds=86400)

# Create middleware stack
middleware = [
    # Rate limiting
    Middleware(
        RateLimitMiddleware,
        limiter=rate_limiter,
        identifier_header="X-Agent-ID",
        excluded_paths=["/health", "/metrics"],
    ),
    # Request deduplication
    Middleware(
        RequestDeduplicationMiddleware,
        deduplicator=deduplicator,
        cache_ttl=3600,
        request_methods=["GET", "HEAD"],
    ),
    # Idempotency
    Middleware(
        IdempotencyMiddleware,
        key_manager=idempotency_manager,
        key_header="Idempotency-Key",
    ),
]

# Create application with middleware
app = BinduApplication(
    manifest=your_agent_manifest,
    middleware=middleware,
    auth_enabled=True,
    debug=False,
)
```

## Error Responses

### Rate Limit Exceeded (429)

```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please slow down.",
    "remaining": 0,
    "reset_in_seconds": 45.3
}
```

## Performance Considerations

### Memory Usage

- **Sliding Window**: O(n) where n = requests in window
- **Token Bucket**: O(1) per identifier
- **Request Cache**: O(1) with LRU cleanup

### Recommendations

1. **For high-throughput APIs**: Use Token Bucket limiter
2. **For precise limits**: Use Sliding Window limiter
3. **For auto-scaling**: Use Adaptive limiter
4. **Cache TTL**: Set based on your idempotency needs (usually 1-24 hours)

### Cleanup

Caches automatically clean up expired entries:
- Every 60 seconds for rate limiters
- On access for small TTLs
- Manual via `cleanup()` method

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/unit/test_rate_limiting_and_deduplication.py -v

# Run specific test class
pytest tests/unit/test_rate_limiting_and_deduplication.py::TestSlidingWindowLimiter -v

# Run with coverage
pytest tests/unit/test_rate_limiting_and_deduplication.py --cov=bindu.utils --cov=bindu.server.middleware
```

## Troubleshooting

### Rate limit too strict?

Increase the `max_requests` or `window_seconds`:
```python
limiter = SlidingWindowLimiter(max_requests=500, window_seconds=60)
```

### High cache memory usage?

Reduce TTL or enable more aggressive cleanup:
```python
dedup = RequestDeduplicator(ttl_seconds=1800)  # 30 minutes
```

### False cache hits?

Ensure request signatures include all relevant data:
```python
signature = await dedup.generate_signature(
    request_data,
    additional_context={
        "user_id": request.user.id,
        "timestamp": int(time.time()),  # Coarse-grained
    }
)
```

## Contributing

To improve these utilities:

1. Add tests for new features
2. Update documentation
3. Submit PR with benchmark results

## Related Documentation

- [Authentication](./AUTHENTICATION.md)
- [Health Checks](./HEALTH_METRICS.md)
- [Observability](./OBSERVABILITY.md)
