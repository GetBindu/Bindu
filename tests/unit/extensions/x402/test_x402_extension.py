"""Tests for x402 extension activation handlers."""

from unittest.mock import MagicMock

from starlette.requests import Request
from starlette.responses import Response

from bindu.extensions.x402.extension import (
    is_activation_requested,
    add_activation_header,
    X402ActivationHandler,
)


class TestIsActivationRequested:
    """Test is_activation_requested function."""

    def test_activation_requested_with_header(self):
        """Test activation is detected when header is present."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://github.com/google-a2a/a2a-x402/v0.1"

        result = is_activation_requested(request)

        assert result is True
        request.headers.get.assert_called_once_with("X-A2A-Extensions", "")

    def test_activation_not_requested_without_header(self):
        """Test activation is not detected when header is absent."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = ""

        result = is_activation_requested(request)

        assert result is False

    def test_activation_not_requested_with_different_extension(self):
        """Test activation is not detected with different extension URI."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://example.com/other-extension"

        result = is_activation_requested(request)

        assert result is False

    def test_activation_requested_with_multiple_extensions(self):
        """Test activation is detected when x402 is among multiple extensions."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://example.com/ext1,https://github.com/google-a2a/a2a-x402/v0.1,https://example.com/ext2"

        result = is_activation_requested(request)

        assert result is True


class TestAddActivationHeader:
    """Test add_activation_header function."""

    def test_add_activation_header_to_response(self):
        """Test that activation header is added to response."""
        response = MagicMock(spec=Response)
        response.headers = {}

        result = add_activation_header(response)

        assert "X-A2A-Extensions" in response.headers
        assert "x402" in response.headers["X-A2A-Extensions"]
        assert result is response

    def test_add_activation_header_preserves_response(self):
        """Test that original response object is returned."""
        response = MagicMock(spec=Response)
        response.headers = {}

        result = add_activation_header(response)

        assert result is response


class TestX402ActivationHandler:
    """Test X402ActivationHandler class."""

    def test_is_requested_method(self):
        """Test is_requested static method."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://github.com/google-a2a/a2a-x402/v0.1"

        result = X402ActivationHandler.is_requested(request)

        assert result is True

    def test_add_header_method(self):
        """Test add_header static method."""
        response = MagicMock(spec=Response)
        response.headers = {}

        result = X402ActivationHandler.add_header(response)

        assert "X-A2A-Extensions" in response.headers
        assert result is response

    def test_check_and_activate_when_requested(self):
        """Test check_and_activate adds header when activation is requested."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://github.com/google-a2a/a2a-x402/v0.1"

        response = MagicMock(spec=Response)
        response.headers = {}

        result = X402ActivationHandler.check_and_activate(request, response)

        assert "X-A2A-Extensions" in response.headers
        assert result is response

    def test_check_and_activate_when_not_requested(self):
        """Test check_and_activate doesn't add header when not requested."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = ""

        response = MagicMock(spec=Response)
        response.headers = {}

        result = X402ActivationHandler.check_and_activate(request, response)

        assert "X-A2A-Extensions" not in response.headers
        assert result is response


class TestX402ExtensionEdgeCases:
    """Test edge cases for x402 extension activation."""

    def test_activation_with_whitespace_in_header(self):
        """Test activation detection with whitespace in header."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = (
            " https://github.com/google-a2a/a2a-x402/v0.1 "
        )

        result = is_activation_requested(request)

        # Should still detect even with whitespace
        assert result is True

    def test_activation_with_case_sensitive_uri(self):
        """Test that URI matching is case-sensitive."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://GITHUB.COM/GOOGLE-A2A/A2A-X402/V0.1"

        result = is_activation_requested(request)

        # URIs are case-sensitive, should not match
        assert result is False

    def test_add_header_with_existing_headers(self):
        """Test adding activation header when other headers exist."""
        response = MagicMock(spec=Response)
        response.headers = {
            "Content-Type": "application/json",
            "X-Custom-Header": "value",
        }

        add_activation_header(response)

        # Should preserve existing headers
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-Custom-Header"] == "value"
        assert "X-A2A-Extensions" in response.headers

    def test_activation_handler_methods_are_static(self):
        """Test that handler methods can be called without instance."""
        # Should not raise error when called as static methods
        request = MagicMock(spec=Request)
        request.headers.get.return_value = ""

        response = MagicMock(spec=Response)
        response.headers = {}

        # Call without creating instance
        X402ActivationHandler.is_requested(request)
        X402ActivationHandler.add_header(response)
        X402ActivationHandler.check_and_activate(request, response)

    def test_activation_with_partial_uri_match(self):
        """Test that partial URI match doesn't trigger activation."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "https://github.com/google-a2a/a2a-x402/v0.0"

        result = is_activation_requested(request)

        assert result is False

    def test_activation_with_uri_as_substring(self):
        """Test activation when URI appears as substring."""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = (
            "prefix-https://github.com/google-a2a/a2a-x402/v0.1-suffix"
        )

        result = is_activation_requested(request)

        # Should still detect as substring
        assert result is True
