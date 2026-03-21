# Bindu Test Suite

Comprehensive test suite for the Bindu A2A protocol implementation.

## Test Structure

```
tests/
├── fixtures/                       # Organized test fixtures
│   ├── __init__.py
│   ├── auth_fixtures.py           # Authentication fixtures
│   ├── storage_fixtures.py        # Storage & scheduler fixtures
│   ├── payment_fixtures.py        # Payment/x402 fixtures
│   └── mock_fixtures.py           # Mock agents & services
├── helpers/                        # Test utilities
│   ├── __init__.py
│   ├── builders.py                # Test data builders (fluent API)
│   └── assertions.py              # Custom assertion helpers
├── unit/                          # Unit tests (fast, isolated)
│   ├── auth/                      # Authentication tests
│   ├── common/                    # Common protocol tests
│   ├── extensions/                # Extension tests
│   │   ├── did/                   # DID extension tests
│   │   └── x402/                  # Payment extension tests
│   ├── server/                    # Server component tests
│   │   ├── endpoints/             # API endpoint tests
│   │   ├── handlers/              # Request handler tests
│   │   ├── middleware/            # Middleware tests
│   │   ├── scheduler/             # Scheduler tests
│   │   ├── storage/               # Storage layer tests
│   │   └── workers/               # Worker tests
│   ├── utils/                     # Utility function tests
│   ├── observability/             # Monitoring tests
│   └── tunneling/                 # Tunneling tests
├── integration/                   # Integration tests
├── edge_cases/                    # Edge case & regression tests
├── e2e/                          # End-to-end tests
├── conftest.py                   # Pytest configuration
├── conftest_stubs.py             # External dependency stubs
├── utils.py                      # Legacy test utilities
└── mocks.py                      # Mock objects
```

## Running Tests

### Run All Tests
```bash
uv run pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Specific test file
uv run pytest tests/unit/test_protocol_types.py

# Specific test class
uv run pytest tests/unit/test_storage.py::TestTaskStorage

# Specific test
uv run pytest tests/unit/test_storage.py::TestTaskStorage::test_save_and_load_task
```

### Run with Coverage
```bash
# Run with coverage and enforce minimum threshold
uv run pytest --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

### Run with Markers
```bash
# Run only unit tests
pytest -m unit


# Run only asyncio tests
pytest -m asyncio

# Exclude slow tests
pytest -m "not slow"
```

### Verbose Output
```bash
# Extra verbose
pytest -vv

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

## Test Coverage

Current test coverage by module:

- **Protocol Types**: Message, Task, Artifact, Context validation
- **Storage**: CRUD operations, concurrency, data integrity
- **Scheduler**: Task queuing, FIFO ordering, lifecycle
- **ManifestWorker**: Hybrid pattern (normal, input-required, auth-required)
- **TaskManager**: All JSON-RPC handlers
- **Postman Scenarios**: Complete A2A protocol flows

## Writing New Tests

### Test File Template
```python
"""Description of what this module tests."""

import pytest
from tests.helpers import TaskBuilder, MessageBuilder, assert_task_state


class TestFeatureName:
    """Test specific feature."""

    @pytest.mark.asyncio
    async def test_specific_behavior(self, memory_storage):
        """Test description."""
        # Arrange - Use builders for clean test data creation
        message = MessageBuilder().with_text("Test request").build()

        # Act
        task = await memory_storage.submit_task(message["context_id"], message)

        # Assert - Use custom assertions
        loaded = await memory_storage.load_task(task["id"])
        assert_task_state(loaded, "submitted")
```

### Using Fixtures

All fixtures are organized in `tests/fixtures/` modules:

**Storage Fixtures** (`tests/fixtures/storage_fixtures.py`):
- `memory_storage`: InMemoryStorage instance
- `memory_scheduler`: InMemoryScheduler instance

**Mock Fixtures** (`tests/fixtures/mock_fixtures.py`):
- `mock_agent`: Mock agent with normal responses
- `mock_agent_input_required`: Mock agent requiring input
- `mock_agent_auth_required`: Mock agent requiring auth
- `mock_agent_error`: Mock agent that raises errors
- `mock_manifest`: Mock AgentManifest
- `mock_manifest_with_push`: Manifest with push notifications
- `mock_did_extension`: Mock DID extension
- `mock_notification_service`: Mock notification service

**Auth Fixtures** (`tests/fixtures/auth_fixtures.py`):
- `mock_hydra_client`: Mock Hydra OAuth client
- `mock_auth_middleware`: Mock authentication middleware

**Payment Fixtures** (`tests/fixtures/payment_fixtures.py`):
- `mock_payment_requirements`: Valid payment requirements dict
- `mock_payment_payload`: Valid payment payload dict
- `mock_facilitator_client`: Mock facilitator client

### Using Test Builders

Test builders provide a fluent API for creating test data:

```python
from tests.helpers import TaskBuilder, MessageBuilder, ContextBuilder, ArtifactBuilder

# Build a task with custom properties
task = (
    TaskBuilder()
    .with_state("working")
    .with_context_id("ctx-123")
    .with_history([msg1, msg2])
    .build()
)

# Build a message
message = (
    MessageBuilder()
    .with_text("Hello, agent!")
    .with_role("user")
    .build()
)

# Build a context
context = (
    ContextBuilder()
    .with_id("ctx-123")
    .with_metadata({"key": "value"})
    .build()
)

# Build an artifact
artifact = (
    ArtifactBuilder()
    .with_text("Result data", mime_type="text/plain")
    .build()
)
```

### Using Custom Assertions

Custom assertions provide clear error messages:

```python
from tests.helpers import (
    assert_task_state,
    assert_jsonrpc_error,
    assert_jsonrpc_success,
    assert_valid_uuid,
    assert_dict_contains,
    assert_list_length,
)

# Assert task state
assert_task_state(task, "completed")

# Assert JSON-RPC responses
assert_jsonrpc_error(response, -32001)  # With specific error code
assert_jsonrpc_success(response)

# Assert UUID validity
assert_valid_uuid(task["id"])

# Assert dict contains expected keys/values
assert_dict_contains(actual, {"key": "value"})

# Assert list length
assert_list_length(items, 5)
```

## Continuous Integration

Tests are run automatically on:
- Every commit (unit tests)
- Pull requests (all tests)
- Main branch (all tests + coverage)

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure bindu is installed in development mode
uv sync --dev
```

**Async warnings:**
```bash
# Install pytest-asyncio
uv add --dev pytest-asyncio
```

**Fixture not found:**
```bash
# Check conftest.py is in the right location
# Fixtures are auto-discovered from conftest.py
```

**Tests hanging:**
```bash
# Add timeout to async tests
pytest --timeout=10
```

## Test Organization Guidelines

### Directory Structure Rules

1. **Mirror source code structure**: Tests in `tests/unit/` should mirror `bindu/` structure
2. **One test file per module**: Each source module gets one corresponding test file
3. **Group related tests**: Use test classes to group related test methods
4. **Separate concerns**: Unit tests in `unit/`, integration in `integration/`, edge cases in `edge_cases/`

### Naming Conventions

**Test Files**: `test_<module_name>.py`
```
bindu/server/storage/postgres_storage.py → tests/unit/server/storage/test_postgres_storage.py
```

**Test Classes**: `Test<FeatureName>` (PascalCase)
```python
class TestPostgresStorage:
    class TestCRUDOperations:
        ...
    class TestConcurrency:
        ...
```

**Test Methods**: `test_<behavior>_<condition>` (snake_case)
```python
def test_save_task_creates_new_record(self):
def test_load_task_returns_none_when_not_found(self):
def test_concurrent_writes_maintain_consistency(self):
```

## Test Principles

1. **DRY**: Use fixtures and builders to avoid duplication
2. **Clear Structure**: Follow Arrange-Act-Assert pattern
3. **Async-First**: All I/O tests use pytest-asyncio
4. **Isolation**: Each test is independent, no shared state
5. **Fast**: Unit tests < 100ms, integration tests < 1s
6. **Readable**: Descriptive names, clear assertions with messages
7. **Maintainable**: Tests mirror source structure for easy navigation

## Test Quality Standards

Each test must:
- ✅ Be independent (no shared state between tests)
- ✅ Be deterministic (no random failures)
- ✅ Have clear arrange/act/assert structure
- ✅ Use descriptive assertion messages
- ✅ Test one behavior per test method
- ✅ Use appropriate fixtures (not inline mocks)
- ✅ Document edge cases with comments

## Contributing

### Adding New Tests

1. **Identify the module** to test
2. **Create test file** in corresponding `tests/unit/` directory
3. **Use builders** for test data creation
4. **Use fixtures** for dependencies
5. **Write clear assertions** with custom helpers
6. **Follow naming conventions**

### Test Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 80%+ overall coverage
- **Critical modules**: 90%+ coverage (storage, endpoints, extensions)
- **New code**: Must include tests (enforced in PR review)

### Before Submitting PR

1. ✅ All tests pass locally
2. ✅ Coverage hasn't decreased
3. ✅ New tests follow structure guidelines
4. ✅ Test names are descriptive
5. ✅ No flaky tests introduced
