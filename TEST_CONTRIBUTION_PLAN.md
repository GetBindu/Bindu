# Test Contribution Plan for Bindu

## Overview
Target: Increase test coverage from ~70% to 80%+
Approach: Start with easiest modules, build up complexity

---

## Priority Order (Easiest First)

### 🎯 Tier 1: Quick Wins (1-2 hours each)

| Module | Why Easy | Files to Test |
|--------|----------|---------------|
| `bindu/settings.py` | Configuration-only, no complex logic | 1 file |
| `bindu/cli/` | Simple CLI with argparse | 1-2 files |
| `bindu/common/` | Data models mostly | 1-2 files |

### 🎯 Tier 2: Moderate (2-4 hours each)

| Module | Why Moderate | Files to Test |
|--------|--------------|---------------|
| `bindu/penguin/did_setup.py` | DID generation logic | ~2 files |
| `bindu/tunneling/` | Tunnel management | ~3 files |
| `bindu/server/handlers/` | Request handlers | ~4 files |

### 🎯 Tier 3: Advanced (4+ hours)

| Module | Why Hard | Files to Test |
|--------|----------|---------------|
| `bindu/grpc/` | Async gRPC, requires mock servers | ~4 files |
| `bindu/server/task_manager.py` | Complex async state machine | ~2 files |

---

## How Tests Are Structured

Location: `tests/unit/<module>/`

Example:
```
tests/unit/
├── penguin/
│   ├── __init__.py
│   ├── test_bindufy.py      # Tests for bindufy.py
│   └── test_manifest.py     # Tests for manifest.py
└── server/
    ├── test_applications.py
    └── test_task_manager.py
```

### Test Pattern (from test_applications.py):

```python
"""Tests for Bindu application server."""

from unittest.mock import Mock
from bindu.server.applications import BinduApplication


class TestBinduApplicationModule:
    """Test module-level functionality."""

    def test_module_imports(self):
        """Test that module imports correctly."""
        assert hasattr(applications, "BinduApplication")


class TestBinduApplicationInitialization:
    """Test class initialization."""

    def test_init_with_minimal_config(self):
        """Test initialization with minimal config."""
        mock_manifest = Mock(spec=AgentManifest)
        app = BinduApplication(manifest=mock_manifest)
        assert app is not None
```

---

## Step-by-Step Guide

### Step 1: Run Existing Tests (Verify Setup)
```bash
cd /Users/konalsmac/MEGA/Bindu
uv run pytest tests/unit/ -v --tb=short
```

### Step 2: Pick a Module from Tier 1
Start with `bindu/settings.py` - it's pure configuration.

### Step 3: Explore the Module
```python
# Read the module to understand what needs testing
# Example: bindu/settings.py
```

### Step 4: Create Test File
```bash
# Create: tests/unit/test_settings.py
# Or: tests/unit/settings/test_settings.py
```

### Step 5: Run New Tests
```bash
uv run pytest tests/unit/test_settings.py -v
```

### Step 6: Verify Coverage Improved
```bash
uv run pytest --cov=bindu.settings --cov-report=term-missing
```

---

## Specific Tasks

### Task 1: Test `bindu/settings.py`
**Files**: 1 (settings.py, ~1000 lines)
**Coverage Goal**: 70%+

What to test:
- Settings loading from environment
- Default values
- Validation logic
- Section parsing (Auth, Storage, etc.)

### Task 2: Test `bindu/cli/`
**Files**: 2-3
**Coverage Goal**: 60%+

What to test:
- Argument parsing
- Serve command
- Error handling
- Help output

### Task 3: Test `bindu/common/`
**Files**: ~5
**Coverage Goal**: 70%+

What to test:
- Model serialization/deserialization
- AgentManifest creation
- DeploymentConfig validation

### Task 4: Test `bindu/penguin/did_setup.py`
**Files**: 2
**Coverage Goal**: 70%+

What to test:
- DID generation from author+name
- Key pair generation
- DID document creation

---

## Running Tests

### Run All Unit Tests
```bash
uv run pytest tests/unit/ -v
```

### Run With Coverage
```bash
uv run pytest tests/unit/ --cov=bindu --cov-report=term-missing
```

### Run Specific Module
```bash
uv run pytest tests/unit/penguin/ -v
```

### Run Single Test File
```bash
uv run pytest tests/unit/server/test_applications.py -v
```

---

## Tips

1. **Use mocks** - Don't hit actual databases or networks
2. **Test edge cases** - Empty inputs, None values, invalid types
3. **Follow existing patterns** - Look at tests/unit/server/test_applications.py
4. **Name clearly** - `test_<function>_<expected_behavior>`
5. **One assertion per test** - Easier to debug

---

## Resources

- pytest docs: https://docs.pytest.org/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- Coverage: https://coverage.readthedocs.io/

---

*Ready to start? Pick Task 1 (settings.py) and create `tests/unit/test_settings.py`*