"""Unit tests for MetricsMiddleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from bindu.server.middleware.metrics import MetricsMiddleware


@pytest.fixture
def mock_app():
    """Mock ASGI app."""
    return AsyncMock()


@pytest.fixture
def middleware(mock_app):
    """Create MetricsMiddleware instance."""
    return MetricsMiddleware(mock_app)


@pytest.fixture
def mock_metrics():
    """Mock get_metrics return value."""
    with patch("bindu.server.middleware.metrics.get_metrics") as mock:
        yield mock.return_value


@pytest.mark.asyncio
async def test_skip_metrics_endpoint(middleware, mock_metrics):
    """Test that requests to /metrics are not recorded."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/metrics"
    
    call_next = AsyncMock(return_value=Response("ok"))
    
    await middleware.dispatch(mock_request, call_next)
    
    # Verify metrics were NOT recorded
    mock_metrics.increment_requests_in_flight.assert_not_called()
    mock_metrics.record_http_request.assert_not_called()


@pytest.mark.asyncio
async def test_record_tokens_success(middleware, mock_metrics):
    """Test that metrics are recorded for successful requests."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/api/test"
    mock_request.method = "POST"
    mock_request.headers = {"content-length": "100"}
    
    response = Response("response body")
    call_next = AsyncMock(return_value=response)
    
    await middleware.dispatch(mock_request, call_next)
    
    # Verify requests in flight increment/decrement
    mock_metrics.increment_requests_in_flight.assert_called_once()
    mock_metrics.decrement_requests_in_flight.assert_called_once()
    
    # Verify record_http_request called
    mock_metrics.record_http_request.assert_called_once()
    args = mock_metrics.record_http_request.call_args
    assert args[0][0] == "POST"
    assert args[0][1] == "/api/test"
    assert args[0][2] == "200"
    # Duration is harder to assert exact value, just type check
    assert isinstance(args[0][3], float)
    assert args[1]["request_size"] == 100
    # Response content length might be 0 or calculated based on body
    # For generated Response("response body"), len is 13
    assert args[1]["response_size"] == 13


@pytest.mark.asyncio
async def test_record_error_handling(middleware, mock_metrics):
    """Test that errors during metric recording don't crash request."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/api/test"
    
    call_next = AsyncMock(return_value=Response("ok"))
    
    # Simulate error in recording
    mock_metrics.record_http_request.side_effect = Exception("Metrics DB down")
    
    # Should not raise exception
    response = await middleware.dispatch(mock_request, call_next)
    
    assert response.status_code == 200
    mock_metrics.decrement_requests_in_flight.assert_called_once()  # cleanup always runs
