# Circuit Breaker

A state-based failure isolation mechanism that prevents retry storms and cascading failures in Bindu's distributed agent system.

## Why Retry Alone Is Insufficient

Tenacity retries handle **transient** failures well — a brief network blip gets retried and succeeds. But when a downstream service is **persistently unavailable**:

| With retries only | With retries + circuit breaker |
|---|---|
| Every call retries N times | First few calls retry, then circuit **opens** |
| Multiple workers retry simultaneously | Opened circuit **blocks** all workers instantly |
| Latency grows linearly with attempts | Fail-fast response (< 1 ms) |
| Downstream gets hammered while down | Downstream gets **zero** traffic during recovery |

The circuit breaker wraps the **entire retry loop** — when open, no retries are attempted at all.

## State Machine

```
        ┌─────────┐
        │ CLOSED  │  ← Normal operation
        └────┬────┘
             │ failures >= failure_threshold
             ▼
        ┌─────────┐
        │  OPEN   │  ← All calls blocked (fail-fast)
        └────┬────┘
             │ recovery_timeout elapsed
             ▼
       ┌──────────┐
       │ HALF_OPEN│  ← Probing with limited calls
       └────┬─────┘
           / \
     success   failure
         │        │
         ▼        ▼
     CLOSED     OPEN
```

## Configuration

Set via environment variables (all optional):

```bash
BINDU_CB_ENABLED=true              # Enable circuit breaker (default: false)
BINDU_CB_FAILURE_THRESHOLD=3       # Failures before OPEN (default: 3)
BINDU_CB_RECOVERY_TIMEOUT=30       # Seconds in OPEN before HALF_OPEN (default: 30)
BINDU_CB_SUCCESS_THRESHOLD=1       # Successes in HALF_OPEN to CLOSE (default: 1)
```

When `BINDU_CB_ENABLED=false` (default), the system behaves exactly as before — full backward compatibility.

## Usage

### Automatic (via retry decorators)

The circuit breaker is **automatically wired** into all existing retry decorators when enabled. No code changes needed:

```python
from bindu.utils.retry import retry_worker_operation

@retry_worker_operation()
async def send_to_service(data):
    # If this fails repeatedly, the circuit opens and
    # subsequent calls fail-fast with CircuitBreakerOpenError
    await external_service.send(data)
```

### Standalone

```python
from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

cb = CircuitBreaker(
    name="payment-gateway",
    failure_threshold=5,
    recovery_timeout=60,
)

try:
    result = await cb.call(payment_api.charge, amount=100)
except CircuitBreakerOpenError as e:
    # Fast-fail path — no network call made
    log.warning(f"Payment circuit open, retry after {e.retry_after:.0f}s")
```

### Using the decorator

```python
from bindu.utils.circuit_breaker import with_circuit_breaker

@with_circuit_breaker("email-service")
async def send_email(to, subject, body):
    await smtp_client.send(to, subject, body)
```

## Per-Operation Isolation

Each retry decorator creates a **separate circuit breaker** keyed by `{type}:{function_name}`:

- `worker:run_agent_task`
- `storage:save_result`
- `api:call_openai`

A failing storage backend does not affect API circuits.

## Logging

State transitions are logged via the standard Bindu logging system:

```
Circuit breaker [storage:save_result] closed → open (failures=3)
Circuit breaker [storage:save_result] open → half_open (failures=3)
Circuit breaker [storage:save_result] half_open → closed (failures=0)
```
