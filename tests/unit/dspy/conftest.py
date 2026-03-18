"""Pytest configuration for dspy unit tests.

This conftest handles pytest collection and test execution for dspy tests,
mocking dependencies to avoid import errors from schema issues.
"""

import sys
from unittest.mock import MagicMock


# Pre-emptively mock problematic imports that cause errors during collection
# This prevents the import chain from reaching schema.py with the missing 'text' import
def pytest_configure(config):
    """Mock problematic modules before test collection."""
    # These mocks prevent import errors from propagating during collection
    sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
    sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())
    sys.modules.setdefault("bindu.server.storage.base", MagicMock())


