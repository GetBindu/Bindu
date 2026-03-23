"""Reusable HTTP client with retry logic and session management.

This module provides a base HTTP client that can be used across the codebase
to avoid duplicating HTTP request logic, retry mechanisms, and session management.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import aiohttp

from bindu.utils.exceptions import (
    HTTPConnectionError,
    HTTPTimeoutError,
    HTTPClientError,
    HTTPServerError,
)
from bindu.utils.logging import get_logger
from bindu.utils.retry import create_retry_decorator

logger = get_logger("bindu.utils.http_client")


class AsyncHTTPClient:
    """Async HTTP client with session management and error handling.

    Features:
    - Automatic session management with context manager support
    - SSL verification control
    - Configurable timeouts
    - Request/response logging
    - Retry logic via decorators on public methods
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        verify_ssl: bool = True,
        max_retries: int = 3,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL for all requests (e.g., https://api.example.com)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts (used by retry decorators)
            default_headers: Default headers to include in all requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.default_headers = default_headers or {}
        self._session: aiohttp.ClientSession | None = None

        logger.debug(f"HTTP client initialized: base_url={base_url}")

    async def __aenter__(self) -> "AsyncHTTPClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.default_headers,
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request with single attempt.

        Retry logic is handled by decorators on public methods.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: URL query parameters
            data: Form data to send
            json: JSON data to send
            headers: Additional headers for this request
            **kwargs: Additional arguments for aiohttp request

        Returns:
            HTTP response

        Raises:
            HTTPClientError: For 4xx client errors
            HTTPServerError: For 5xx server errors
            HTTPConnectionError: If connection fails
            HTTPTimeoutError: If request times out
        """
        await self._ensure_session()
        assert self._session is not None

        # Build full URL
        url = (
            f"{self.base_url}{endpoint}"
            if endpoint.startswith("/")
            else f"{self.base_url}/{endpoint}"
        )

        # Merge headers
        request_headers = {**self.default_headers, **(headers or {})}

        try:
            async with self._session.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=request_headers,
                **kwargs,
            ) as response:
                # Check for client/server errors and raise appropriate exceptions
                if 400 <= response.status < 500:
                    error_text = await response.text()
                    logger.error(f"{method} {url} -> {response.status}: {error_text}")
                    raise HTTPClientError(
                        f"Client error: {error_text}",
                        status=response.status,
                        url=url,
                    )
                elif response.status >= 500:
                    error_text = await response.text()
                    logger.warning(f"{method} {url} -> {response.status}: {error_text}")
                    raise HTTPServerError(
                        f"Server error: {error_text}",
                        status=response.status,
                        url=url,
                    )

                # Read response body before context manager closes
                response_data = await response.read()
                # Store data in response for later access
                response._body = response_data

                logger.debug(f"{method} {url} -> {response.status}")
                return response

        except asyncio.TimeoutError as e:
            logger.warning(f"{method} {url} timed out")
            raise HTTPTimeoutError("Request timed out", url=url) from e

        except (
            aiohttp.ClientConnectorError,
            aiohttp.ServerDisconnectedError,
        ) as e:
            logger.warning(f"{method} {url} connection failed: {e}")
            raise HTTPConnectionError(f"Connection failed: {str(e)}", url=url) from e

    @create_retry_decorator("api")
    async def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make GET request with automatic retry.

        Args:
            endpoint: API endpoint
            params: URL query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request(
            "GET", endpoint, params=params, headers=headers, **kwargs
        )

    @create_retry_decorator("api")
    async def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make POST request with automatic retry.

        Args:
            endpoint: API endpoint
            data: Form data to send
            json: JSON data to send
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request(
            "POST", endpoint, data=data, json=json, headers=headers, **kwargs
        )

    @create_retry_decorator("api")
    async def put(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make PUT request with automatic retry.

        Args:
            endpoint: API endpoint
            data: Form data to send
            json: JSON data to send
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request(
            "PUT", endpoint, data=data, json=json, headers=headers, **kwargs
        )

    @create_retry_decorator("api")
    async def delete(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make DELETE request with automatic retry.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request("DELETE", endpoint, headers=headers, **kwargs)

    @create_retry_decorator("api")
    async def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make PATCH request with automatic retry.

        Args:
            endpoint: API endpoint
            data: Form data to send
            json: JSON data to send
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request(
            "PATCH", endpoint, data=data, json=json, headers=headers, **kwargs
        )


@asynccontextmanager
async def http_client(
    base_url: str,
    timeout: int = 10,
    verify_ssl: bool = True,
    max_retries: int = 3,
    default_headers: dict[str, str] | None = None,
):
    """Context manager for creating and managing an HTTP client.

    Usage:
        async with http_client("https://api.example.com") as client:
            response = await client.get("/endpoint")
            data = await response.json()

    Args:
        base_url: Base URL for all requests
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        max_retries: Maximum number of retry attempts
        default_headers: Default headers for all requests

    Yields:
        AsyncHTTPClient instance
    """
    client = AsyncHTTPClient(
        base_url=base_url,
        timeout=timeout,
        verify_ssl=verify_ssl,
        max_retries=max_retries,
        default_headers=default_headers,
    )
    try:
        await client._ensure_session()
        yield client
    finally:
        await client.close()
