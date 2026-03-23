"""Minimal tests for endpoint utilities."""

from unittest.mock import Mock

from bindu.server.endpoints.utils import (
    get_client_ip,
    jsonrpc_error,
)


class TestEndpointUtils:
    """Test endpoint utility functions."""

    def test_get_client_ip_with_client(self):
        """Test extracting client IP from request."""
        mock_request = Mock()
        mock_request.client.host = "192.168.1.1"

        ip = get_client_ip(mock_request)

        assert ip == "192.168.1.1"

    def test_get_client_ip_without_client(self):
        """Test extracting client IP when client is None."""
        mock_request = Mock()
        mock_request.client = None

        ip = get_client_ip(mock_request)

        assert ip == "unknown"

    def test_jsonrpc_error_basic(self):
        """Test creating JSON-RPC error response."""
        response = jsonrpc_error(code=-32600, message="Invalid Request")

        assert response.status_code == 400
        assert b"Invalid Request" in response.body
        assert b"-32600" in response.body

    def test_jsonrpc_error_with_data(self):
        """Test creating JSON-RPC error with additional data."""
        response = jsonrpc_error(
            code=-32602,
            message="Invalid params",
            data="Missing required field",
            request_id="123",
        )

        assert response.status_code == 400
        assert b"Invalid params" in response.body
        assert b"Missing required field" in response.body
        assert b"123" in response.body

    def test_jsonrpc_error_custom_status(self):
        """Test creating JSON-RPC error with custom HTTP status."""
        response = jsonrpc_error(code=-32603, message="Internal error", status=500)

        assert response.status_code == 500
