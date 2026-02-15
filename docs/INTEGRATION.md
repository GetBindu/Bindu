# Quick Integration Guide

## 🚀 How to Add Resilience to Your Bindu Agent (5 minutes)

### Step 1: Copy the Files

Copy these files to your Bindu project:
```
bindu/utils/circuit_breaker.py
bindu/utils/rate_limiter.py
```

### Step 2: Update Your Agent

**Before (Basic Agent):**
```python
from bindu.penguin.bindufy import bindufy

def handler(messages: list[dict[str, str]]):
    result = agent.run(input=messages)
    return result

config = {
    "author": "your.email@example.com",
    "name": "my_agent",
    "description": "My agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
}

bindufy(config, handler)
```

**After (Resilient Agent):**
```python
from bindu.penguin.bindufy import bindufy
from bindu.utils.circuit_breaker import CircuitBreaker
from bindu.utils.rate_limiter import TokenBucketRateLimiter
import asyncio

# Setup resilience patterns
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="my_agent"
)

rate_limiter = TokenBucketRateLimiter(
    rate=100,
    per_seconds=60,
    burst_size=20,
    name="my_agent"
)

def handler(messages: list[dict[str, str]]):
    async def protected_handler():
        async with rate_limiter:
            async with circuit_breaker:
                result = agent.run(input=messages)
                return result
    
    return asyncio.run(protected_handler())

config = {
    "author": "your.email@example.com",
    "name": "my_agent",
    "description": "My resilient agent with circuit breaker and rate limiting",
    "deployment": {"url": "http://localhost:3773", "expose": True},
}

bindufy(config, handler)
```

### Step 3: Add Health Endpoint (Optional)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "circuit_breaker": circuit_breaker.get_status(),
        "rate_limiter": rate_limiter.get_status()
    }
```

### Step 4: Monitor Metrics

```python
# Get circuit breaker status
status = circuit_breaker.get_status()
print(f"Circuit State: {status['state']}")
print(f"Success Rate: {status['metrics']['success_rate']}%")

# Get rate limiter status
status = rate_limiter.get_status()
print(f"Requests: {status['accepted_requests']}/{status['total_requests']}")
print(f"Available: {status['available_tokens']} tokens")
```

## 🎛️ Configuration Examples

### Conservative (High Reliability)
```python
CircuitBreaker(failure_threshold=3, recovery_timeout=120)
TokenBucketRateLimiter(rate=50, per_seconds=60, burst_size=10)
```

### Balanced (Production)
```python
CircuitBreaker(failure_threshold=5, recovery_timeout=60)
TokenBucketRateLimiter(rate=100, per_seconds=60, burst_size=20)
```

### Aggressive (High Throughput)
```python
CircuitBreaker(failure_threshold=10, recovery_timeout=30)
TokenBucketRateLimiter(rate=200, per_seconds=60, burst_size=50)
```

### Adaptive (Smart)
```python
CircuitBreaker(failure_threshold=5, recovery_timeout=60)
AdaptiveRateLimiter(base_rate=100, min_rate=20, max_rate=200)
```

## 🏗️ Multi-Agent Setup

For systems with multiple agents:

```python
from bindu.utils.circuit_breaker import CircuitBreakerRegistry
from bindu.utils.rate_limiter import RateLimiterRegistry

# Create registries
breakers = CircuitBreakerRegistry()
limiters = RateLimiterRegistry()

# Setup agents
AGENTS = {
    "research": {"threshold": 5, "rate": 100},
    "data_processor": {"threshold": 3, "rate": 50},
    "summarizer": {"threshold": 10, "rate": 200},
}

for name, config in AGENTS.items():
    breakers.get_or_create(name, failure_threshold=config["threshold"])
    limiters.create_token_bucket(name, rate=config["rate"], per_seconds=60)

# Use in handlers
def make_handler(agent_name):
    breaker = breakers.get(agent_name)
    limiter = limiters.get(agent_name)
    
    def handler(messages):
        async def protected():
            async with limiter:
                async with breaker:
                    return agents[agent_name].run(input=messages)
        return asyncio.run(protected())
    
    return handler
```

## 📊 Monitoring Integration

### Prometheus Metrics

```python
from prometheus_client import Gauge, Counter

# Circuit breaker metrics
circuit_state_gauge = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state',
    ['agent']
)

circuit_failures_counter = Counter(
    'circuit_breaker_failures',
    'Circuit breaker failures',
    ['agent']
)

# Update periodically
def update_metrics():
    for name, status in breakers.get_all_statuses().items():
        state_value = {"closed": 0, "half_open": 1, "open": 2}[status['state']]
        circuit_state_gauge.labels(agent=name).set(state_value)
        circuit_failures_counter.labels(agent=name).inc(
            status['metrics']['failed_requests']
        )
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log circuit state changes
def log_circuit_events():
    status = circuit_breaker.get_status()
    if status['state'] == 'open':
        logger.warning(
            f"Circuit breaker opened for {status['name']}: "
            f"{status['failure_count']} failures"
        )
    elif status['state'] == 'closed':
        logger.info(f"Circuit breaker closed for {status['name']}")
```

## 🔍 Debugging

### Check if Circuit is Open

```python
if circuit_breaker.is_open:
    print("⚠️ Circuit breaker is OPEN - requests will fail fast")
    print(f"Time until retry: {circuit_breaker.recovery_timeout}s")
```

### Check Rate Limit Status

```python
status = rate_limiter.get_status()
if status['rejected_requests'] > 0:
    print(f"⚠️ {status['rejected_requests']} requests were rate limited")
    print(f"Acceptance rate: {status['acceptance_rate']}%")
```

### Force Recovery (Testing Only)

```python
# Force close circuit (testing/debugging)
await circuit_breaker.force_close()

# Force open circuit (maintenance mode)
await circuit_breaker.force_open()
```

## 🚨 Common Issues

### Issue 1: Too Many Circuit Opens

**Symptom**: Circuit breaker frequently opens
**Solution**:
```python
# Increase threshold or timeout
CircuitBreaker(
    failure_threshold=10,  # Was 5
    recovery_timeout=120   # Was 60
)
```

### Issue 2: Too Many Rate Limit Rejections

**Symptom**: High rejection rate
**Solution**:
```python
# Increase rate or use adaptive
AdaptiveRateLimiter(
    base_rate=200,  # Was 100
    max_rate=400
)
```

### Issue 3: Slow Recovery

**Symptom**: Circuit stays open too long
**Solution**:
```python
# Reduce recovery timeout
CircuitBreaker(
    recovery_timeout=30,  # Was 60
    success_threshold=1   # Was 2
)
```

## ✅ Testing Your Integration

```python
# Test circuit breaker
print("Testing circuit breaker...")
for i in range(10):
    try:
        async with circuit_breaker:
            if i < 6:
                raise Exception("Test failure")
            print(f"Request {i}: Success")
    except Exception as e:
        print(f"Request {i}: {e}")
    
    status = circuit_breaker.get_status()
    print(f"State: {status['state']}")

# Test rate limiter
print("\nTesting rate limiter...")
for i in range(30):
    try:
        async with rate_limiter:
            print(f"Request {i}: Allowed")
    except RateLimitExceeded as e:
        print(f"Request {i}: Rate limited - {e}")
```

## 📚 Next Steps

1. ✅ Run the demo: `python demo.py`
2. ✅ Read full docs: `RESILIENCE.md`
3. ✅ Check examples: See usage patterns above
4. ✅ Monitor in production: Add metrics/logging
5. ✅ Tune configuration: Adjust based on your needs

## 🎯 Quick Reference

| Pattern | Use When | Configuration |
|---------|----------|---------------|
| Circuit Breaker | Calling external services | `threshold=5, timeout=60` |
| Token Bucket | Smooth rate limiting | `rate=100/min, burst=20` |
| Sliding Window | Precise rate limits | `max=100, window=60s` |
| Adaptive | Variable load | `base=100, range=[10,200]` |

---

**Questions?** Check `RESILIENCE.md` or run `python demo.py`
