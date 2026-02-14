"""Reusable HTTP client with retry logic and session management.

This module provides a base HTTP client that can be used across the codebase
to avoid duplicating HTTP request logic, retry mechanisms, and session management.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import aiohttp

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.http_client")


class AsyncHTTPClient:
    """Async HTTP client with automatic retry, session management, and error handling.

    Features:
    - Automatic session management with context manager support
    - Exponential backoff retry logic
    - SSL verification control
    - Configurable timeouts
    - Request/response logging
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        verify_ssl: bool = True,
        max_retries: int = 3,
        default_headers: Optional[Dict[str, str]] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL for all requests (e.g., https://api.example.com)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts for failed requests
            default_headers: Default headers to include in all requests
            cert_file: Path to client certificate file (PEM)
            key_file: Path to client private key file (PEM)
            ca_file: Path to CA certificate file (PEM)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.default_headers = default_headers or {}

        # mTLS configuration
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file

        self._session: Optional[aiohttp.ClientSession] = None

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
            import ssl

            ssl_context: bool | ssl.SSLContext = True

            # Configure SSL context if certificates provided
            if self.cert_file and self.key_file:
                ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                ssl_context.load_cert_chain(
                    certfile=self.cert_file, keyfile=self.key_file
                )
                if self.ca_file:
                    ssl_context.load_verify_locations(cafile=self.ca_file)

            # If no certs but verify_ssl is False, use unverified context
            elif not self.verify_ssl:
                ssl_context = False

            connector = aiohttp.TCPConnector(ssl=ssl_context)
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
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_on_status: Optional[list[int]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: URL query parameters
            data: Form data to send
            json: JSON data to send
            headers: Additional headers for this request
            retry_on_status: List of status codes to retry on (default: 5xx)
            **kwargs: Additional arguments for aiohttp request

        Returns:
            HTTP response

        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        await self._ensure_session()

        # Build full URL
        url = (
            f"{self.base_url}{endpoint}"
            if endpoint.startswith("/")
            else f"{self.base_url}/{endpoint}"
        )

        # Merge headers
        request_headers = {**self.default_headers, **(headers or {})}

        # Default retry on server errors
        retry_statuses = retry_on_status or list(range(500, 600))

        for attempt in range(self.max_retries):
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
                    # Check if we should retry
                    if (
                        response.status in retry_statuses
                        and attempt < self.max_retries - 1
                    ):
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"{method} {url} returned {response.status}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Read response body before context manager closes
                    response_data = await response.read()
                    # Store data in response for later access
                    response._body = response_data

                    logger.debug(f"{method} {url} -> {response.status}")
                    return response

            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Connection error: {e}, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Request failed after {self.max_retries} retries: {e}"
                    )
                    raise

        raise aiohttp.ClientError(f"Request failed after {self.max_retries} retries")

    async def get(
        self,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make GET request.

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

    async def post(
        self,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make POST request.

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

    async def put(
        self,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make PUT request.

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

    async def delete(
        self,
        endpoint: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make DELETE request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            HTTP response
        """
        return await self.request("DELETE", endpoint, headers=headers, **kwargs)

    async def patch(
        self,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make PATCH request.

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
    default_headers: Optional[Dict[str, str]] = None,
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
