---
description: Run comprehensive tests and validate code changes for Bindu
---

# Bindu Testing Workflow

Use this workflow to run tests, validate code quality, and ensure changes don't break functionality.

## Quick Reference

```bash
# Run all tests with coverage
uv run pytest --cov=bindu --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_applications.py -v

# Run pre-commit hooks
uv run pre-commit run --all-files

# Full validation (tests + hooks + type checking)
uv run pytest && uv run pre-commit run --all-files
```

---

## Step 1: Pre-Test Checks

Ensure your environment is ready:

```bash
# Check Python version
python --version  # Should be 3.12+

# Verify uv is installed
uv --version

# Install dependencies
uv sync
```

---

## Step 2: Run Unit Tests

```bash
# Run all unit tests with verbose output
uv run pytest tests/unit/ -v

# Run with coverage report
uv run pytest tests/unit/ --cov=bindu --cov-report=term-missing

# Run specific test class
uv run pytest tests/unit/test_applications.py::TestBinduApplication -v

# Run specific test method
uv run pytest tests/unit/test_applications.py::TestBinduApplication::test_initialization -v
```

### Common Test Patterns

| Test Type | Command |
|-----------|---------|
| All tests | `uv run pytest` |
| Unit only | `uv run pytest tests/unit/` |
| Integration | `uv run pytest tests/integration/` |
| With markers | `uv run pytest -m x402` |
| Fast (no slow) | `uv run pytest -m "not slow"` |

---

## Step 3: Run Integration Tests

```bash
# Run integration tests (requires services)
uv run pytest tests/integration/ -v

# Skip integration tests
uv run pytest -m "not integration"
```

### Integration Test Requirements

- **PostgreSQL**: For storage backend tests
- **Redis**: For scheduler backend tests
- **Environment variables**: Set in `.env.test` or export manually

---

## Step 4: Code Quality Checks

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Run specific hooks
uv run pre-commit run ruff --all-files
uv run pre-commit run pytest --all-files
uv run pre-commit run bandit --all-files
uv run pre-commit run detect-secrets --all-files
uv run pre-commit run pydocstyle --all-files
```

### Pre-Commit Hooks

- **pytest**: Run tests with 66% coverage requirement
- **ruff**: Linting and formatting
- **bandit**: Security checks
- **detect-secrets**: Prevent credential leaks
- **pydocstyle**: Documentation style

---

## Step 5: Test Specific Components

### Test Observability Module

```bash
uv run pytest tests/unit/test_sentry.py -v
uv run pytest tests/unit/test_openinference.py -v
```

### Test Extensions

```bash
# DID extension
uv run pytest tests/unit/test_did_extension.py -v

# X402 payment extension
uv run pytest tests/unit/test_x402_extension.py -v
uv run pytest tests/unit/test_x402_utils.py -v
```

### Test Storage Backends

```bash
# Memory storage
uv run pytest tests/unit/test_memory_storage.py -v

# PostgreSQL storage (requires DB)
uv run pytest tests/integration/test_postgres_storage.py -v
```

---

## Step 6: Generate Coverage Report

```bash
# Generate HTML coverage report
uv run pytest --cov=bindu --cov-report=html

# Open report in browser
open htmlcov/index.html
```

---

## Step 7: Continuous Testing

For development, use pytest-watch:

```bash
# Install pytest-watch
uv add --dev pytest-watch

# Watch for changes and re-run tests
uv run ptw -- -v
```

---

## Troubleshooting

### Tests Fail with Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall

# Clear pytest cache
rm -rf .pytest_cache
```

### Coverage Below Threshold

```bash
# Find uncovered lines
uv run pytest --cov=bindu --cov-report=term-missing | grep -A 5 "TOTAL"

# Focus on specific module
uv run pytest tests/unit/test_applications.py --cov=bindu.server.applications --cov-report=term-missing
```

### Pre-Commit Hook Failures

```bash
# Update hooks
uv run pre-commit autoupdate

# Clear hook cache
uv run pre-commit clean

# Re-run failed hook
uv run pre-commit run <hook-name> --all-files
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_isready

# Check Redis is running
redis-cli ping

# Use memory backends for testing
export STORAGE_BACKEND=memory
export SCHEDULER_BACKEND=memory
```

---

## Test Artifacts

All test runs generate artifacts in `.local/`:

```bash
# Create .local directory
mkdir -p .local

# Generate test results JSON
uv run pytest --json-report --json-report-file=.local/test-results.json
```

---

## Full Validation Script

Save as `scripts/validate.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> Running unit tests..."
uv run pytest tests/unit/ -v --cov=bindu --cov-report=term-missing

echo "==> Running pre-commit hooks..."
uv run pre-commit run --all-files

echo "==> Checking coverage threshold..."
uv run pytest --cov=bindu --cov-fail-under=66

echo "==> All validations passed! ✅"
```

Make executable:

```bash
chmod +x scripts/validate.sh
./scripts/validate.sh
```

---

## CI/CD Integration

For GitHub Actions, tests run automatically on:

- Push to `main`
- Pull requests
- Manual workflow dispatch

Check `.github/workflows/` for CI configuration.

---

## Best Practices

1. **Run tests before committing**: Use pre-commit hooks
2. **Maintain coverage**: Keep above 66% threshold
3. **Test edge cases**: Don't just test happy paths
4. **Use fixtures**: Reuse test setup with pytest fixtures
5. **Mock external services**: Don't rely on external APIs in unit tests
6. **Fast tests**: Keep unit tests fast (<1s each)
7. **Descriptive names**: Use clear test method names
8. **One assertion per test**: Focus tests on single behaviors

---

## Next Steps

After tests pass:

1. Review coverage report for gaps
2. Add tests for new features
3. Update documentation if needed
4. Run `/workflow deployment` to deploy changes
5. Create release with `/workflow release`
