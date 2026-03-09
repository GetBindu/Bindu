"""Unit tests for HydraMiddleware (Pure ASGI Refactor)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bindu.server.middleware.auth.hydra import HydraMiddleware


@pytest.fixture
def mock_hydra_config():
    """Mock Hydra configuration."""
    config = MagicMock()
    config.admin_url = "https://hydra-admin.test.com"
    config.public_url = "https://hydra.test.com"
    config.timeout = 10
    config.verify_ssl = False
    config.public_endpoints = [
        "/.well-known/agent.json",
        "/docs*",
        "/favicon.ico",
    ]
    return config


@pytest.fixture
def mock_app():
    """Mock the downstream ASGI application."""
    return AsyncMock()


@pytest.fixture
def hydra_middleware(mock_app, mock_hydra_config):
    """Create HydraMiddleware instance."""
    return HydraMiddleware(mock_app, mock_hydra_config)


@pytest.fixture
def make_asgi_scope():
    """Helper to create standard ASGI HTTP scopes."""

    def _make_scope(path="/", method="GET", headers=None, query_string=b""):
        return {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string,
            "headers": headers or [],
        }

    return _make_scope


@pytest.fixture
def make_ws_scope():
    """Helper to create ASGI WebSocket scopes."""

    def _make_scope(path="/", headers=None, query_string=b""):
        return {
            "type": "websocket",
            "path": path,
            "query_string": query_string,
            "headers": headers or [],
        }

    return _make_scope


@pytest.mark.asyncio
async def test_public_endpoint_bypass(hydra_middleware, mock_app, make_asgi_scope):
    """Test that public endpoints bypass authentication."""
    scope = make_asgi_scope(path="/docs/api")
    receive = AsyncMock()
    send = AsyncMock()

    await hydra_middleware(scope, receive, send)

    # Application should be called directly, skipping auth
    mock_app.assert_called_once_with(scope, receive, send)
    send.assert_not_called()


@pytest.mark.asyncio
async def test_missing_token_returns_401(hydra_middleware, mock_app, make_asgi_scope):
    """Test that missing token returns 401 via pure ASGI."""
    scope = make_asgi_scope(path="/api/protected")
    receive = AsyncMock()
    send = AsyncMock()

    await hydra_middleware(scope, receive, send)

    mock_app.assert_not_called()

    # Assert JSON-RPC Error was sent
    assert send.call_count == 2
    response_start = send.call_args_list[0][0][0]
    response_body = send.call_args_list[1][0][0]

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 401

    body = json.loads(response_body["body"].decode())
    assert "error" in body
    assert body["id"] is None  # DoS protection check


@pytest.mark.asyncio
async def test_valid_token_allows_access(hydra_middleware, mock_app, make_asgi_scope):
    """Test that valid token allows access and attaches context."""
    scope = make_asgi_scope(
        path="/api/protected", headers=[(b"authorization", b"Bearer valid_token_123")]
    )
    receive = AsyncMock()
    send = AsyncMock()

    introspection_result = {
        "active": True,
        "sub": "user-123",
        "client_id": "agent-abc",
        "exp": 9999999999,
        "iat": 1234567890,
        "scope": "agent:read agent:write",
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        await hydra_middleware(scope, receive, send)

        mock_app.assert_called_once_with(scope, receive, send)

        # Verify user context was attached to the ASGI state
        assert "state" in scope
        assert scope["state"]["authenticated"] is True
        assert scope["state"]["user"]["sub"] == "user-123"


@pytest.mark.asyncio
async def test_websocket_token_extraction(hydra_middleware, mock_app, make_ws_scope):
    """Test that tokens can be extracted from WebSocket subprotocols."""
    # Simulate a websocket connection with a token in the subprotocol
    scope = make_ws_scope(
        path="/api/stream",
        headers=[(b"sec-websocket-protocol", b"v1, bearer-ws_token_123")],
    )
    receive = AsyncMock()
    send = AsyncMock()

    introspection_result = {
        "active": True,
        "sub": "ws-user-123",
        "exp": 9999999999,
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        await hydra_middleware(scope, receive, send)

        mock_app.assert_called_once()
        assert scope["state"]["user"]["sub"] == "ws-user-123"


@pytest.mark.asyncio
async def test_query_param_token_extraction(
    hydra_middleware, mock_app, make_asgi_scope
):
    """Test token extraction from URL query parameters as a fallback."""
    scope = make_asgi_scope(
        path="/api/protected", query_string=b"other=123&token=query_token_456"
    )
    receive = AsyncMock()
    send = AsyncMock()

    introspection_result = {
        "active": True,
        "sub": "query-user",
        "exp": 9999999999,
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        await hydra_middleware(scope, receive, send)

        mock_app.assert_called_once()
        assert scope["state"]["user"]["sub"] == "query-user"


@pytest.mark.asyncio
async def test_inactive_token_returns_401(hydra_middleware, mock_app, make_asgi_scope):
    """Test that inactive token returns 401."""
    scope = make_asgi_scope(
        path="/api/protected", headers=[(b"authorization", b"Bearer inactive_token")]
    )
    receive = AsyncMock()
    send = AsyncMock()

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value={"active": False}),
    ):
        await hydra_middleware(scope, receive, send)

        mock_app.assert_not_called()

        # Verify 401 response
        assert send.call_count == 2
        assert send.call_args_list[0][0][0]["status"] == 401


@pytest.mark.asyncio
async def test_token_cache_hit(hydra_middleware, mock_app, make_asgi_scope):
    """Test that token cache prevents duplicate network calls."""
    scope = make_asgi_scope(
        path="/api/protected", headers=[(b"authorization", b"Bearer cached_token")]
    )
    receive = AsyncMock()
    send = AsyncMock()

    introspection_result = {
        "active": True,
        "sub": "user-123",
        "exp": 9999999999,
    }

    mock_introspect = AsyncMock(return_value=introspection_result)

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=mock_introspect,
    ):
        # First request - should call introspect
        await hydra_middleware(scope, receive, send)
        assert mock_introspect.call_count == 1

        # Second request - should use cache and not call introspect again
        await hydra_middleware(scope, receive, send)
        assert mock_introspect.call_count == 1
        assert mock_app.call_count == 2


def test_is_public_endpoint_regex(hydra_middleware):
    """Test that the pre-compiled regex correctly matches paths."""
    assert hydra_middleware._is_public_endpoint("/.well-known/agent.json") is True
    assert hydra_middleware._is_public_endpoint("/docs") is True
    assert (
        hydra_middleware._is_public_endpoint("/docs/api/v1") is True
    )  # tests the /docs* glob
    assert hydra_middleware._is_public_endpoint("/") is False
    assert hydra_middleware._is_public_endpoint("/api/protected") is False
