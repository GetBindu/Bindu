"""Authentication-related test fixtures."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_hydra_client() -> MagicMock:
    """Create a mock Hydra OAuth client for testing.

    Returns:
        MagicMock: Mock Hydra client with common methods stubbed
    """
    client = MagicMock()
    client.introspect_token.return_value = {
        "active": True,
        "sub": "test-user-id",
        "scope": "read write",
    }
    client.get_login_request.return_value = {
        "challenge": "test-challenge",
        "subject": "test-user",
    }
    return client


@pytest.fixture
def mock_auth_middleware() -> MagicMock:
    """Create a mock authentication middleware for testing.

    Returns:
        MagicMock: Mock middleware that allows all requests
    """
    middleware = MagicMock()
    middleware.authenticate.return_value = True
    return middleware
