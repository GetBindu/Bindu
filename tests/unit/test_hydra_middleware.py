"""Unit tests for HydraMiddleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import JSONResponse

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
        "/docs",
        "/favicon.ico",
    ]
    return config


@pytest.fixture
def hydra_middleware(mock_hydra_config):
    """Create HydraMiddleware instance."""
    app = MagicMock()
    return HydraMiddleware(app, mock_hydra_config)


@pytest.mark.asyncio
async def test_public_endpoint_bypass(hydra_middleware):
    """Test that public endpoints bypass authentication."""
    request = MagicMock(spec=Request)
    request.url.path = "/docs"

    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

    response = await hydra_middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_missing_token_returns_401(hydra_middleware):
    """Test that missing token returns 401."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = None

    call_next = AsyncMock()

    response = await hydra_middleware.dispatch(request, call_next)

    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_valid_token_allows_access(hydra_middleware):
    """Test that valid token allows access."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = "Bearer valid_token_123"
    request.state = MagicMock()

    # Mock token introspection
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
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

        response = await hydra_middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

        # Verify user context was attached
        assert hasattr(request.state, "user")
        assert request.state.authenticated is True


@pytest.mark.asyncio
async def test_inactive_token_returns_401(hydra_middleware):
    """Test that inactive token returns 401."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = "Bearer inactive_token"

    # Mock token introspection with inactive token
    introspection_result = {
        "active": False,
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        call_next = AsyncMock()

        response = await hydra_middleware.dispatch(request, call_next)

        assert response.status_code == 401
        call_next.assert_not_called()


@pytest.mark.asyncio
async def test_expired_token_returns_401(hydra_middleware):
    """Test that expired token returns 401."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = "Bearer expired_token"

    # Mock token introspection with expired token
    introspection_result = {
        "active": True,
        "sub": "user-123",
        "exp": 1234567890,  # Past timestamp
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        call_next = AsyncMock()

        response = await hydra_middleware.dispatch(request, call_next)

        assert response.status_code == 401
        call_next.assert_not_called()


@pytest.mark.asyncio
async def test_token_cache_hit(hydra_middleware):
    """Test that token cache is used for repeated requests."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = "Bearer cached_token"
    request.state = MagicMock()

    introspection_result = {
        "active": True,
        "sub": "user-123",
        "client_id": "agent-abc",
        "exp": 9999999999,
        "iat": 1234567890,
        "scope": "agent:read",
    }

    mock_introspect = AsyncMock(return_value=introspection_result)

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=mock_introspect,
    ):
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

        # First request - should call introspect
        await hydra_middleware.dispatch(request, call_next)
        assert mock_introspect.call_count == 1

        # Second request - should use cache
        await hydra_middleware.dispatch(request, call_next)
        assert mock_introspect.call_count == 1  # Still 1, not 2


@pytest.mark.asyncio
async def test_m2m_token_identification(hydra_middleware):
    """Test that M2M tokens are correctly identified."""
    request = MagicMock(spec=Request)
    request.url.path = "/"
    request.headers.get.return_value = "Bearer m2m_token"
    request.state = MagicMock()

    # M2M token has client_credentials grant type
    introspection_result = {
        "active": True,
        "sub": "agent-123",
        "client_id": "agent-abc",
        "exp": 9999999999,
        "token_type": "access_token",
        "grant_type": "client_credentials",
        "scope": "agent:read agent:write",
    }

    with patch.object(
        hydra_middleware.hydra_client,
        "introspect_token",
        new=AsyncMock(return_value=introspection_result),
    ):
        call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

        response = await hydra_middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert request.state.user["is_m2m"] is True
        assert request.state.user["sub"] == "agent-123"


def test_extract_token_from_header(hydra_middleware):
    """Test token extraction from Authorization header."""
    request = MagicMock(spec=Request)

    # Valid Bearer token
    request.headers.get.return_value = "Bearer test_token_123"
    token = hydra_middleware._extract_token(request)
    assert token == "test_token_123"

    # Invalid format
    request.headers.get.return_value = "test_token_123"
    token = hydra_middleware._extract_token(request)
    assert token is None

    # Missing header
    request.headers.get.return_value = None
    token = hydra_middleware._extract_token(request)
    assert token is None


def test_is_public_endpoint(hydra_middleware):
    """Test public endpoint detection."""
    assert hydra_middleware._is_public_endpoint("/docs") is True
    assert hydra_middleware._is_public_endpoint("/.well-known/agent.json") is True
    assert hydra_middleware._is_public_endpoint("/") is False
    assert hydra_middleware._is_public_endpoint("/api/protected") is False
