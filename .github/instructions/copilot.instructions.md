# Bindu Codebase Patterns

**Always reuse existing code - no redundancy!**

## Tech Stack

- **Runtime**: Python 3.12+
- **Package Manager**: uv (keep `uv.lock` in sync)
- **Framework**: Starlette (async ASGI)
- **Testing**: pytest with coverage (66% minimum)
- **Lint/Format**: ruff (`uv run pre-commit run --all-files`)
- **Type Checking**: ty (optional)
- **Database**: PostgreSQL (asyncpg) or in-memory
- **Scheduler**: Redis or in-memory
- **Protocol**: A2A (Agent-to-Agent)

## Anti-Redundancy Rules

- Avoid files that just re-export from another file. Import directly from the original source.
- If a function already exists, import it - do NOT create a duplicate.
- Before creating any utility or helper, search for existing implementations first.
- Use `bindu.settings.app_settings` for all configuration - never hardcode values.

## Source of Truth Locations

### Settings (`bindu/settings.py`)

- **All configuration**: `app_settings.{module}.{setting}`
- **Never hardcode**: URLs, ports, timeouts, API keys, feature flags

**NEVER create local config constants - use `app_settings`.**

### Storage (`bindu/server/storage/`)

- Base interface: `bindu/server/storage/base.py` (`StorageBackend`)
- Memory: `bindu/server/storage/memory.py` (`MemoryStorage`)
- PostgreSQL: `bindu/server/storage/postgres.py` (`PostgresStorage`)

### Scheduler (`bindu/server/scheduler/`)

- Base interface: `bindu/server/scheduler/base.py` (`SchedulerBackend`)
- Memory: `bindu/server/scheduler/memory.py` (`MemoryScheduler`)
- Redis: `bindu/server/scheduler/redis.py` (`RedisScheduler`)

### Extensions (`bindu/extensions/`)

- DID: `bindu/extensions/did/` (Decentralized Identity)
- x402: `bindu/extensions/x402/` (Payment protocol)

### Observability (`bindu/observability/`)

- OpenInference: `bindu/observability/openinference.py` (`setup()`)
- Sentry: `bindu/observability/sentry.py` (`init_sentry()`)

## Import Conventions

- Use absolute imports: `from bindu.server.storage import StorageBackend`
- Type-only imports: `from typing import TYPE_CHECKING` + `if TYPE_CHECKING:`
- Settings: `from bindu.settings import app_settings`
- Never use relative imports across packages

## Code Quality

- Python 3.12+, type hints required
- Keep files under ~500 LOC - extract modules when larger
- Tests in `tests/unit/` and `tests/integration/`
- Run `uv run pre-commit run --all-files` before commits
- Maintain 66% test coverage minimum

## Architecture Patterns

### Application Structure

```python
from bindu import BinduApplication

app = BinduApplication(
    name="My Agent",
    author="author@example.com",
    description="Agent description"
)

@app.task
async def my_task(message: str) -> str:
    return f"Processed: {message}"

if __name__ == "__main__":
    app.serve(launch=True)  # Starts with tunnel
```

### Storage Pattern

```python
from bindu.settings import app_settings

# Get configured storage backend
storage = app.storage  # Auto-configured from settings

# Use storage
await storage.save_task(task)
task = await storage.get_task(task_id)
```

### Extension Pattern

```python
from bindu.extensions.did import DIDAgentExtension

# Extensions are auto-loaded from manifest
did_ext = app.manifest.did_extension
did = did_ext.did  # Access DID
```

## Testing Patterns

### Unit Tests

```python
import pytest
from bindu.server.applications import BinduApplication

@pytest.mark.asyncio
async def test_application_creation():
    app = BinduApplication(name="Test", author="test@example.com")
    assert app.name == "Test"
```

### Fixtures

```python
@pytest.fixture
def app():
    return BinduApplication(
        name="Test Agent",
        author="test@example.com"
    )
```

## Stack & Commands

- **Package manager**: uv (`uv sync`)
- **Run server**: `uv run bindu serve --launch`
- **Tests**: `uv run pytest`
- **Coverage**: `uv run pytest --cov=bindu`
- **Lint/format**: `uv run pre-commit run --all-files`
- **Type-check**: `uv run ty check bindu/ `
- **Migrations**: `uv run alembic upgrade head`

## Versioning

- **Format**: Week-based CalVer (`YYYY.W.D`)
  - YYYY = Year
  - W = ISO week number (1-53)
  - D = Day of week (1=Sunday, 7=Saturday)
- **Example**: `2026.8.3` (Year 2026, Week 8, Wednesday)

## Security Best Practices

- Never commit secrets (use `.env` files)
- Use `app_settings` for sensitive config
- Validate all external input
- Use type hints for input validation
- Run `detect-secrets` pre-commit hook
- Review security impact in PRs

## Common Mistakes to Avoid

❌ **Don't**: Hardcode configuration values
✅ **Do**: Use `app_settings.{module}.{setting}`

❌ **Don't**: Create duplicate utility functions
✅ **Do**: Search for existing implementations first

❌ **Don't**: Use `print()` for logging
✅ **Do**: Use `logger` from `bindu.utils.logging`

❌ **Don't**: Skip tests
✅ **Do**: Maintain 66% coverage minimum

❌ **Don't**: Commit without running pre-commit hooks
✅ **Do**: Run `uv run pre-commit run --all-files`

## File Organization

```
bindu/
├── server/           # Core server components
│   ├── applications.py
│   ├── endpoints/    # API endpoints
│   ├── storage/      # Storage backends
│   └── scheduler/    # Scheduler backends
├── extensions/       # Optional extensions
│   ├── did/         # DID extension
│   └── x402/        # Payment extension
├── observability/    # Monitoring & tracing
├── utils/           # Shared utilities
└── settings.py      # Configuration (source of truth)

tests/
├── unit/            # Unit tests
└── integration/     # Integration tests
```

## When Coding with Humans

- Run commands manually (don't use automation scripts)
- Explain changes clearly
- Ask for clarification when uncertain
- Follow the PR template for all changes
- Ensure all tests pass before submitting
