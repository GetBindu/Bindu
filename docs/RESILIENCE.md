# Production Resilience for Bindu Agents

> **Circuit Breakers, Rate Limiting, and Auto-Recovery for Production-Grade AI Agents**

## 🎯 Overview

This feature adds production-grade resilience patterns to Bindu agents, enabling them to:
- **Fail fast** when downstream services are unhealthy (Circuit Breaker)
- **Throttle requests** to prevent overload (Rate Limiting)
- **Auto-recover** from transient failures
- **Monitor health** with detailed metrics

## 📦 Components

### 1. Circuit Breaker (`circuit_breaker.py`)

Prevents cascading failures by monitoring error rates and "opening" the circuit when failures exceed threshold.

**States:**
- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: Too many failures, requests fail fast
- **HALF_OPEN**: Testing recovery, limited requests allowed

**Key Features:**
- Configurable failure threshold and recovery timeout
- Half-open state for gradual recovery
- Detailed metrics and state transitions
- Thread-safe for concurrent requests
- Registry for managing multiple circuit breakers

### 2. Rate Limiter (`rate_limiter.py`)

Controls request rate to prevent overload and ensure fair resource allocation.

**Implementations:**
- **TokenBucketRateLimiter**: Smooth rate limiting with bursts
- **SlidingWindowRateLimiter**: Precise rate control over rolling window
- **AdaptiveRateLimiter**: Automatically adjusts based on error rates

**Key Features:**
- Multiple rate limiting strategies
- Configurable rates and windows
- Burst support for traffic spikes
- Adaptive adjustment based on system health
- Registry for per-agent limits

## 🚀 Quick Start

### Basic Circuit Breaker

```python
from circuit_breaker import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60.0,    # Try recovery after 60s
    name="agent_communication"
)

# Protect agent calls
async def call_agent():
    async with breaker:
        response = await agent.send_message(...)
        return response
```

### Basic Rate Limiting

```python
from rate_limiter import TokenBucketRateLimiter

# Create rate limiter
limiter = TokenBucketRateLimiter(
    rate=100,           # 100 requests per minute
    per_seconds=60,
    burst_size=20,      # Allow bursts up to 20
    name="agent_requests"
)

# Rate limit requests
async def make_request():
    async with limiter:
        response = await agent.send_message(...)
        return response
```

## 💡 Usage Examples

### Example 1: Resilient Agent Communication

```python
from circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from rate_limiter import TokenBucketRateLimiter

class ResilientAgent:
    def __init__(self, name: str):
        self.name = name
        
        # Circuit breaker for failure protection
        self.breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            name=f"{name}_breaker"
        )
        
        # Rate limiter for request throttling
        self.limiter = TokenBucketRateLimiter(
            rate=100,
            per_seconds=60,
            burst_size=20,
            name=f"{name}_limiter"
        )
    
    async def send_message(self, message: str):
        """Send message with resilience patterns."""
        try:
            async with self.limiter:
                async with self.breaker:
                    # Your agent communication logic
                    response = await self._communicate(message)
                    return response
        except RateLimitExceeded as e:
            return {"error": "rate_limited", "retry_after": e.retry_after}
        except CircuitBreakerOpenError as e:
            return {"error": "service_unavailable", "message": str(e)}
```

### Example 2: Multi-Agent System

```python
from circuit_breaker import CircuitBreakerRegistry
from rate_limiter import RateLimiterRegistry

# Create registries
breakers = CircuitBreakerRegistry()
limiters = RateLimiterRegistry()

# Configure each agent
agents = ["research", "data_processing", "summarizer"]
for agent in agents:
    breakers.get_or_create(agent, failure_threshold=3)
    limiters.create_token_bucket(agent, rate=50, per_seconds=60)

# Use in agent communication
async def call_agent(agent_name: str, message: str):
    breaker = breakers.get(agent_name)
    limiter = limiters.get(agent_name)
    
    async with limiter:
        async with breaker:
            return await communicate(agent_name, message)
```

### Example 3: Adaptive Rate Limiting

```python
from rate_limiter import AdaptiveRateLimiter

# Rate limiter that adjusts based on errors
limiter = AdaptiveRateLimiter(
    base_rate=100,
    min_rate=10,
    max_rate=200,
    window_seconds=60,
    error_threshold=0.1,  # 10% errors trigger adjustment
    adjustment_factor=0.2  # 20% adjustment
)

async def make_request():
    try:
        async with limiter:
            response = await agent.send_message(...)
            return response
    except Exception as e:
        # Limiter tracks errors and adjusts rate automatically
        raise
```

### Example 4: Monitoring and Metrics

```python
# Get circuit breaker status
status = breaker.get_status()
print(f"State: {status['state']}")
print(f"Success Rate: {status['metrics']['success_rate']}%")
print(f"Failures: {status['failure_count']}")

# Get rate limiter status
status = limiter.get_status()
print(f"Accepted: {status['accepted_requests']}")
print(f"Rejected: {status['rejected_requests']}")
print(f"Available Tokens: {status['available_tokens']}")

# Registry-wide monitoring
all_breakers = breakers.get_all_statuses()
open_circuits = breakers.get_open_circuits()
```

## 🔧 Configuration Guide

### Circuit Breaker Configuration

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|-------------|
| `failure_threshold` | Failures before opening | 5 | 3-10 based on criticality |
| `recovery_timeout` | Seconds before retry | 60.0 | 30-120s |
| `half_open_max_calls` | Max calls in half-open | 3 | 2-5 |
| `success_threshold` | Successes to close | 2 | 2-3 |
| `expected_exception` | Exception type to count | `Exception` | Your specific error type |

### Rate Limiter Configuration

**Token Bucket:**
| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `rate` | Requests per window | Based on capacity |
| `per_seconds` | Time window | 60 (1 minute) |
| `burst_size` | Max burst | 10-20% of rate |

**Sliding Window:**
| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `max_requests` | Max in window | Based on capacity |
| `window_seconds` | Rolling window | 60 (1 minute) |

**Adaptive:**
| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `base_rate` | Starting rate | Expected average |
| `min_rate` | Minimum allowed | 10-20% of base |
| `max_rate` | Maximum allowed | 150-200% of base |
| `error_threshold` | Error rate trigger | 0.1 (10%) |
| `adjustment_factor` | Adjustment size | 0.2 (20%) |

## 📊 Monitoring & Observability

### Circuit Breaker Metrics

```python
metrics = breaker.metrics.to_dict()
{
    "total_requests": 100,
    "successful_requests": 85,
    "failed_requests": 10,
    "rejected_requests": 5,
    "success_rate": 85.0,
    "state_transitions": {
        "closed_to_open": 2,
        "open_to_half_open": 1,
        "half_open_to_closed": 1
    }
}
```

### Rate Limiter Metrics

```python
status = limiter.get_status()
{
    "name": "agent_limiter",
    "type": "token_bucket",
    "rate": 100,
    "available_tokens": 45.2,
    "accepted_requests": 950,
    "rejected_requests": 50,
    "acceptance_rate": 95.0
}
```

### Integration with Observability Tools

```python
# Export to Prometheus
from prometheus_client import Gauge

circuit_state = Gauge('circuit_breaker_state', 'Circuit breaker state', ['agent'])
success_rate = Gauge('circuit_breaker_success_rate', 'Success rate', ['agent'])

def export_metrics():
    for name, breaker in breakers.get_all_statuses().items():
        state_value = {"closed": 0, "half_open": 1, "open": 2}[breaker['state']]
        circuit_state.labels(agent=name).set(state_value)
        success_rate.labels(agent=name).set(breaker['metrics']['success_rate'])
```

## 🏗️ Architecture Integration

### Adding to Bindu Agent

```python
from bindu.penguin.bindufy import bindufy
from circuit_breaker import CircuitBreaker
from rate_limiter import TokenBucketRateLimiter

# Your agent setup
agent = Agent(...)

# Add resilience
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
limiter = TokenBucketRateLimiter(rate=100, per_seconds=60)

def handler(messages: list[dict[str, str]]):
    """Handler with resilience patterns."""
    async def resilient_handler():
        async with limiter:
            async with breaker:
                result = agent.run(input=messages)
                return result
    
    return asyncio.run(resilient_handler())

config = {...}
bindufy(config, handler)
```

### Integration Points

1. **API Layer**: Rate limit incoming requests
2. **Agent Communication**: Circuit breaker for agent-to-agent calls
3. **External Services**: Both patterns for third-party APIs
4. **Background Jobs**: Rate limit job execution

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest test_circuit_breaker.py test_rate_limiter.py -v

# Run specific test
pytest test_circuit_breaker.py::test_circuit_breaker_opens_on_failures -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Coverage

- Circuit Breaker: State transitions, recovery, concurrent requests
- Rate Limiter: Token refill, window expiry, burst handling
- Integration: Registry management, metrics tracking

## 🎨 Best Practices

### 1. Choose the Right Pattern

- **Circuit Breaker**: For downstream service failures
- **Rate Limiter**: For request throttling and fairness
- **Both**: For production-critical services

### 2. Configuration

- Start conservative (lower thresholds)
- Monitor and adjust based on metrics
- Different settings for different criticality levels

### 3. Error Handling

```python
try:
    async with limiter:
        async with breaker:
            result = await operation()
except RateLimitExceeded as e:
    # Handle rate limiting
    await asyncio.sleep(e.retry_after)
    retry()
except CircuitBreakerOpenError:
    # Handle circuit open
    return fallback_response()
except Exception as e:
    # Handle other errors
    log_error(e)
```

### 4. Monitoring

- Track metrics continuously
- Alert on circuit breaker opens
- Monitor rate limit rejection rates
- Analyze trends over time

### 5. Graceful Degradation

```python
async def resilient_call():
    try:
        return await primary_agent()
    except CircuitBreakerOpenError:
        return await fallback_agent()  # Fallback to simpler agent
    except RateLimitExceeded:
        return cached_response()  # Return cached data
```

## 🔍 Troubleshooting

### Circuit Breaker Always Open

**Cause**: Failure threshold too low or service actually failing
**Solution**:
- Check underlying service health
- Increase `failure_threshold`
- Increase `recovery_timeout`

### Too Many Rate Limit Rejections

**Cause**: Rate too low for actual traffic
**Solution**:
- Increase `rate` parameter
- Add `burst_size` for traffic spikes
- Use `AdaptiveRateLimiter` for automatic adjustment

### Metrics Not Updating

**Cause**: Not using context manager correctly
**Solution**:
```python
# ❌ Wrong
breaker.acquire()
operation()
breaker.release()

# ✅ Correct
async with breaker:
    operation()
```

## 🚀 Performance Considerations

### Memory Usage

- Circuit Breaker: O(failure_threshold) for recent failures
- Sliding Window: O(max_requests) for timestamps
- Token Bucket: O(1) constant

### Latency Impact

- Circuit Breaker: < 1ms overhead
- Rate Limiter: < 1ms overhead
- Both combined: < 2ms overhead

### Scalability

- Thread-safe for concurrent requests
- Lock contention only on state changes
- Suitable for high-throughput systems

## 📝 Contributing

See the test files for examples of:
- Writing new tests
- Testing edge cases
- Performance benchmarks

## 🔗 Related Documentation

- [Bindu Main README](../README.md)
- [Scheduler Documentation](../docs/SCHEDULER.md)
- [Health Metrics](../docs/HEALTH_METRICS.md)
- [Observability](../docs/OBSERVABILITY.md)

## 📄 License

Apache License 2.0 - Same as Bindu project

## 🙏 Acknowledgments

Inspired by:
- [Netflix Hystrix](https://github.com/Netflix/Hystrix)
- [Resilience4j](https://github.com/resilience4j/resilience4j)
- [Martin Fowler's Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
