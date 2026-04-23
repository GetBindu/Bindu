# Integration Tests

End-to-end tests that verify complete flows with real servers on real network ports. These are slower and less hermetic than unit tests, so they run in CI (every PR) but **not** in pre-commit (every commit).

## Test Structure

```
tests/integration/
  grpc/
    __init__.py
    test_grpc_e2e.py       # Full gRPC + A2A round-trip tests
```

## Running

```bash
# Run all integration tests
uv run pytest tests/integration/ -v -m e2e

# Run just gRPC E2E tests
uv run pytest tests/integration/grpc/ -v -m e2e

# Run with verbose output
uv run pytest tests/integration/grpc/ -v -m e2e -s
```

## gRPC E2E Tests

**File:** `grpc/test_grpc_e2e.py`

These tests verify the complete language-agnostic agent flow — the same path a TypeScript or Kotlin SDK takes when calling `bindufy()`.

### What's tested

| Test | What it proves |
|------|---------------|
| `test_heartbeat_unregistered` | gRPC server starts on test port, accepts Heartbeat calls, returns `acknowledged=false` for unknown agents |
| `test_register_agent` | Full RegisterAgent flow: config validation, DID creation, manifest with GrpcAgentClient, HTTP server started |
| `test_heartbeat_registered` | After registration, Heartbeat returns `acknowledged=true` |
| `test_agent_card_available` | A2A agent card at `/.well-known/agent.json` contains DID, skills, and capabilities |
| `test_send_message_and_get_response` | **Full round-trip**: A2A HTTP message -> TaskManager -> Scheduler -> Worker -> GrpcAgentClient -> MockAgentHandler -> response with DID-signed artifacts |
| `test_health_endpoint` | `/health` endpoint returns 200 on the registered agent's HTTP server |

### Architecture

The tests use a `MockAgentHandler` that simulates what a TypeScript or Kotlin SDK does:

```
Test Process
  |
  |-- Start gRPC server (BinduService) on :13774
  |-- Start MockAgentHandler on :13999
  |-- Call RegisterAgent (config + callback=:13999)
  |     |
  |     |-- Core runs bindufy logic
  |     |-- Creates GrpcAgentClient(:13999)
  |     |-- Starts HTTP/A2A on :13773
  |
  |-- Send A2A message via HTTP to :13773
  |     |
  |     |-- TaskManager -> Scheduler -> Worker
  |     |-- Worker calls GrpcAgentClient(:13999)
  |     |-- MockAgentHandler returns "Echo: ..."
  |     |-- Worker processes response
  |
  |-- Verify task completed with correct content
  |-- Clean up all servers
```

### Ports used

| Port | Purpose |
|------|---------|
| 13773 | HTTP/A2A server (non-standard to avoid conflicts) |
| 13774 | gRPC BinduService (non-standard) |
| 13999 | MockAgentHandler (non-standard) |

Non-standard ports are used to avoid conflicts with a locally running Bindu instance on the default ports (3773/3774).

### MockAgentHandler

The mock handler echoes messages back with a prefix:

```python
class MockAgentHandler(AgentHandlerServicer):
    def HandleMessages(self, request, context):
        last_message = request.messages[-1].content
        return HandleResponse(
            content=f"Echo from mock handler: {last_message}",
            state="",
            is_final=True,
        )
```

This is exactly what a real SDK does — receives messages over gRPC, runs the developer's handler, returns the response.

## Adding New Integration Tests

### For new gRPC features

Add tests to `grpc/test_grpc_e2e.py`. Use the existing `grpc_setup` fixture which handles server lifecycle:

```python
@pytest.mark.e2e
@pytest.mark.slow
def test_my_new_feature(grpc_setup):
    registry, grpc_port = grpc_setup
    # Your test here
```

### For new integration areas

Create a new directory:

```
tests/integration/
  grpc/           # Existing
  payments/       # New area
    __init__.py
    test_x402_e2e.py
```

Mark tests with `@pytest.mark.e2e` and `@pytest.mark.slow`.

## CI Pipeline

Integration tests run in the GitHub Actions CI workflow (`.github/workflows/ci.yml`) on every PR to main. They run **after** unit tests pass:

```
Unit Tests (pre-commit) --> E2E Tests (CI) --> TypeScript SDK Build (CI)
```

## Troubleshooting

### "Port already in use"

Kill processes on the test ports:

```bash
lsof -ti:13773 -ti:13774 -ti:13999 | xargs kill 2>/dev/null
```

### Tests hang

The test fixture has a 30-second timeout for server startup. If tests hang:
- Check if the ports are already occupied
- Check if a previous test run left zombie processes
- Run with `-s` flag to see live output: `uv run pytest tests/integration/grpc/ -v -m e2e -s`

### Tests pass locally but fail in CI

Common causes:
- CI doesn't have `grpcio` installed (check `pyproject.toml` optional deps)
- Port conflicts with other CI jobs (the non-standard ports should prevent this)
- Timing issues — increase sleep/retry values if needed
