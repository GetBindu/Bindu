"""Mock objects and services for testing."""

import pytest

from tests.mocks import (
    MockAgent,
    MockDIDExtension,
    MockManifest,
    MockNotificationService,
)


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a mock agent that returns normal responses.

    Returns:
        MockAgent: Agent that completes tasks successfully
    """
    return MockAgent(response="Test agent response")


@pytest.fixture
def mock_agent_input_required() -> MockAgent:
    """Create a mock agent that requires user input.

    Returns:
        MockAgent: Agent that requests additional input
    """
    return MockAgent(response="What is your name?", response_type="input-required")


@pytest.fixture
def mock_agent_auth_required() -> MockAgent:
    """Create a mock agent that requires authentication.

    Returns:
        MockAgent: Agent that requests authentication
    """
    return MockAgent(response="Please provide API key", response_type="auth-required")


@pytest.fixture
def mock_agent_error() -> MockAgent:
    """Create a mock agent that raises errors.

    Returns:
        MockAgent: Agent that fails execution
    """
    return MockAgent(response="Agent execution failed", response_type="error")


@pytest.fixture
def mock_manifest(mock_agent: MockAgent) -> MockManifest:
    """Create a mock agent manifest with default configuration.

    Args:
        mock_agent: The mock agent to use in the manifest

    Returns:
        MockManifest: Manifest with basic capabilities
    """
    return MockManifest(agent_fn=mock_agent)


@pytest.fixture
def mock_manifest_with_push() -> MockManifest:
    """Create a mock manifest with push notifications enabled.

    Returns:
        MockManifest: Manifest with push notification capability
    """
    return MockManifest(capabilities={"push_notifications": True})


@pytest.fixture
def mock_did_extension() -> MockDIDExtension:
    """Create a mock DID extension for testing.

    Returns:
        MockDIDExtension: DID extension with signing capabilities
    """
    return MockDIDExtension()


@pytest.fixture
def mock_notification_service() -> MockNotificationService:
    """Create a mock notification service for testing.

    Returns:
        MockNotificationService: Service for sending notifications
    """
    return MockNotificationService()
