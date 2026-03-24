"""Common exception types for bindu utilities.

This module defines shared exception types to avoid circular dependencies
between modules like retry.py and http_client.py.
"""

from __future__ import annotations


class HTTPError(Exception):
    """Base exception for all HTTP errors."""

    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        """Initialize HTTP error with message and optional status/URL.

        Args:
            message: Error message
            status: Optional HTTP status code
            url: Optional URL that caused the error
        """
        self.message = message
        self.status = status
        self.url = url
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error message with status and URL if available."""
        parts = [self.message]
        if self.status:
            parts.append(f"Status: {self.status}")
        if self.url:
            parts.append(f"URL: {self.url}")
        return " | ".join(parts)


class HTTPConnectionError(HTTPError):
    """Raised when connection to server fails."""

    pass


class HTTPTimeoutError(HTTPError):
    """Raised when request times out."""

    pass


class HTTPClientError(HTTPError):
    """Raised for 4xx client errors."""

    pass


class HTTPServerError(HTTPError):
    """Raised for 5xx server errors."""

    pass
