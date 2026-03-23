"""Organized test fixtures for Bindu test suite.

This module provides centralized fixture management, split into logical categories:
- auth_fixtures: Authentication and authorization fixtures
- storage_fixtures: Storage layer fixtures (memory, postgres)
- payment_fixtures: Payment and x402 extension fixtures
- mock_fixtures: Mock objects and services
"""

from tests.fixtures.auth_fixtures import *  # noqa: F403
from tests.fixtures.mock_fixtures import *  # noqa: F403
from tests.fixtures.payment_fixtures import *  # noqa: F403
from tests.fixtures.storage_fixtures import *  # noqa: F403

__all__ = [
    # Auth fixtures
    "mock_hydra_client",  # noqa: F405
    "mock_auth_middleware",  # noqa: F405
    # Storage fixtures
    "memory_storage",  # noqa: F405
    "memory_scheduler",  # noqa: F405
    # Payment fixtures
    "mock_payment_requirements",  # noqa: F405
    "mock_payment_payload",  # noqa: F405
    # Mock fixtures
    "mock_agent",  # noqa: F405
    "mock_agent_input_required",  # noqa: F405
    "mock_agent_auth_required",  # noqa: F405
    "mock_agent_error",  # noqa: F405
    "mock_manifest",  # noqa: F405
    "mock_did_extension",  # noqa: F405
    "mock_notification_service",  # noqa: F405
]
