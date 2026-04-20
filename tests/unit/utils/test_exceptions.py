"""Minimal tests for HTTP exceptions."""

import pytest

from bindu.utils.exceptions import (
    HTTPError,
    HTTPConnectionError,
    HTTPTimeoutError,
    HTTPClientError,
    HTTPServerError,
)


class TestHTTPExceptions:
    """Test HTTP exception hierarchy."""

    def test_http_error_base_exception(self):
        """Test HTTPError is base for all HTTP exceptions."""
        error = HTTPError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_http_client_error_4xx(self):
        """Test HTTPClientError for 4xx responses."""
        error = HTTPClientError("Not found", status=404)

        assert isinstance(error, HTTPError)
        assert error.status == 404
        assert "Not found" in str(error)

    def test_http_server_error_5xx(self):
        """Test HTTPServerError for 5xx responses."""
        error = HTTPServerError("Internal error", status=500)

        assert isinstance(error, HTTPError)
        assert error.status == 500

    def test_http_connection_error(self):
        """Test HTTPConnectionError for connection failures."""
        error = HTTPConnectionError("Connection refused")

        assert isinstance(error, HTTPError)
        assert "Connection refused" in str(error)

    def test_http_timeout_error(self):
        """Test HTTPTimeoutError for timeout failures."""
        error = HTTPTimeoutError("Request timeout")

        assert isinstance(error, HTTPError)
        assert "timeout" in str(error).lower()


class TestHTTPError:
    """Test HTTPError base exception."""

    def test_http_error_with_message_only(self):
        """Test creating HTTPError with just a message."""
        error = HTTPError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status is None
        assert error.url is None

    def test_http_error_with_status(self):
        """Test creating HTTPError with status code."""
        error = HTTPError("Bad request", status=400)

        assert "Bad request" in str(error)
        assert "Status: 400" in str(error)
        assert error.status == 400

    def test_http_error_with_url(self):
        """Test creating HTTPError with URL."""
        error = HTTPError("Not found", url="https://example.com/api")

        assert "Not found" in str(error)
        assert "URL: https://example.com/api" in str(error)
        assert error.url == "https://example.com/api"

    def test_http_error_with_all_params(self):
        """Test creating HTTPError with all parameters."""
        error = HTTPError(
            "Server error", status=500, url="https://example.com/api/endpoint"
        )

        error_str = str(error)
        assert "Server error" in error_str
        assert "Status: 500" in error_str
        assert "URL: https://example.com/api/endpoint" in error_str

    def test_http_error_can_be_raised(self):
        """Test that HTTPError can be raised and caught."""
        with pytest.raises(HTTPError) as exc_info:
            raise HTTPError("Test error", status=418)

        assert exc_info.value.message == "Test error"
        assert exc_info.value.status == 418

    def test_http_error_inheritance(self):
        """Test that HTTPError inherits from Exception."""
        error = HTTPError("Test")
        assert isinstance(error, Exception)


class TestHTTPConnectionError:
    """Test HTTPConnectionError exception."""

    def test_connection_error_basic(self):
        """Test creating HTTPConnectionError."""
        error = HTTPConnectionError("Connection refused")

        assert str(error) == "Connection refused"
        assert error.message == "Connection refused"

    def test_connection_error_with_url(self):
        """Test HTTPConnectionError with URL."""
        error = HTTPConnectionError("Failed to connect", url="https://api.example.com")

        assert "Failed to connect" in str(error)
        assert "https://api.example.com" in str(error)

    def test_connection_error_inheritance(self):
        """Test that HTTPConnectionError inherits from HTTPError."""
        error = HTTPConnectionError("Test")
        assert isinstance(error, HTTPError)
        assert isinstance(error, Exception)


class TestHTTPTimeoutError:
    """Test HTTPTimeoutError exception."""

    def test_timeout_error_basic(self):
        """Test creating HTTPTimeoutError."""
        error = HTTPTimeoutError("Request timed out")

        assert str(error) == "Request timed out"
        assert error.message == "Request timed out"

    def test_timeout_error_with_url(self):
        """Test HTTPTimeoutError with URL."""
        error = HTTPTimeoutError("Timeout after 30s", url="https://slow.example.com")

        assert "Timeout after 30s" in str(error)
        assert "https://slow.example.com" in str(error)

    def test_timeout_error_inheritance(self):
        """Test that HTTPTimeoutError inherits from HTTPError."""
        error = HTTPTimeoutError("Test")
        assert isinstance(error, HTTPError)
        assert isinstance(error, Exception)


class TestHTTPClientError:
    """Test HTTPClientError exception."""

    def test_client_error_basic(self):
        """Test creating HTTPClientError."""
        error = HTTPClientError("Bad request", status=400)

        assert "Bad request" in str(error)
        assert "Status: 400" in str(error)

    def test_client_error_404(self):
        """Test HTTPClientError for 404."""
        error = HTTPClientError(
            "Not found", status=404, url="https://api.example.com/missing"
        )

        assert "Not found" in str(error)
        assert "Status: 404" in str(error)
        assert "https://api.example.com/missing" in str(error)

    def test_client_error_inheritance(self):
        """Test that HTTPClientError inherits from HTTPError."""
        error = HTTPClientError("Test")
        assert isinstance(error, HTTPError)
        assert isinstance(error, Exception)


class TestHTTPServerError:
    """Test HTTPServerError exception."""

    def test_server_error_basic(self):
        """Test creating HTTPServerError."""
        error = HTTPServerError("Internal server error", status=500)

        assert "Internal server error" in str(error)
        assert "Status: 500" in str(error)

    def test_server_error_503(self):
        """Test HTTPServerError for 503."""
        error = HTTPServerError(
            "Service unavailable", status=503, url="https://api.example.com/service"
        )

        assert "Service unavailable" in str(error)
        assert "Status: 503" in str(error)
        assert "https://api.example.com/service" in str(error)

    def test_server_error_inheritance(self):
        """Test that HTTPServerError inherits from HTTPError."""
        error = HTTPServerError("Test")
        assert isinstance(error, HTTPError)
        assert isinstance(error, Exception)
