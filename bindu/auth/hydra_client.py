"""Hydra API client for token introspection and OAuth2 management.

This client handles communication with Ory Hydra's Admin API for token operations.
"""

from __future__ import annotations as _annotations

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel

from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_client")


class TokenIntrospectionResult(BaseModel):
    """Result of token introspection from Hydra."""

    active: bool
    sub: Optional[str] = None
    client_id: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    aud: Optional[List[str]] = None
    iss: Optional[str] = None
    scope: Optional[str] = None
    token_type: Optional[str] = None
    username: Optional[str] = None
    ext: Optional[Dict[str, Any]] = None
    grant_type: Optional[str] = None
    nbf: Optional[int] = None


class OAuthClient(BaseModel):
    """OAuth2 client configuration."""

    client_id: str
    client_name: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uris: List[str] = []
    grant_types: List[str] = ["authorization_code", "refresh_token"]
    response_types: List[str] = ["code"]
    scope: str = "openid offline"
    token_endpoint_auth_method: str = "client_secret_basic"
    metadata: Optional[Dict[str, Any]] = None


class HydraClient:
    """Client for interacting with Ory Hydra Admin API.

    Handles token introspection, OAuth2 client management, and other Hydra operations.
    """

    def __init__(
        self,
        admin_url: str,
        public_url: Optional[str] = None,
        timeout: int = 10,
        verify_ssl: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize Hydra client.

        Args:
            admin_url: Hydra Admin API URL (e.g., http://localhost:4445)
            public_url: Hydra Public API URL (e.g., http://localhost:4444)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.admin_url = admin_url.rstrip("/")
        self.public_url = (
            public_url.rstrip("/") if public_url else admin_url.replace("4445", "4444")
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

        logger.debug(
            f"Hydra client initialized: admin={admin_url}, public={self.public_url}"
        )

    async def __aenter__(self) -> "HydraClient":
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
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request_with_retry(
        self, method: str, endpoint: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for aiohttp request

        Returns:
            HTTP response

        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        await self._ensure_session()
        url = f"{self.admin_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                async with self._session.request(method, url, **kwargs) as response:
                    if response.status >= 500 and attempt < self.max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status}, retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status == 404:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=404,
                            message="Endpoint not found",
                        )

                    return response

            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Connection error: {e}, retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise aiohttp.ClientError(f"Request failed after {self.max_retries} retries")

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """Introspect OAuth2 token using Hydra Admin API.

        Args:
            token: OAuth2 access token

        Returns:
            Token introspection result

        Raises:
            ValueError: If token introspection fails
            aiohttp.ClientError: If HTTP request fails
        """
        data = {
            "token": token,
            "scope": "",  # Optional: specify required scopes
        }

        try:
            response = await self._request_with_retry(
                "POST", "/admin/oauth2/introspect", data=data
            )

            if response.status != 200:
                error_text = await response.text()
                logger.error(
                    f"Token introspection failed: {response.status} - {error_text}"
                )
                raise ValueError(f"Hydra introspection failed: {error_text}")

            result_data = await response.json()
            logger.debug(
                f"Token introspection successful: active={result_data.get('active')}"
            )

            return result_data

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during token introspection: {e}")
            raise ValueError(f"Failed to introspect token: {str(e)}")

    async def create_oauth_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new OAuth2 client in Hydra.

        Args:
            client_data: OAuth2 client configuration

        Returns:
            Created client information
        """
        try:
            response = await self._request_with_retry(
                "POST", "/admin/clients", json=client_data
            )

            if response.status not in (200, 201):
                error_text = await response.text()
                raise ValueError(f"Failed to create OAuth client: {error_text}")

            return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Failed to create OAuth client: {e}")
            raise

    async def get_oauth_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth2 client information.

        Args:
            client_id: Client ID to retrieve

        Returns:
            Client information or None if not found
        """
        try:
            response = await self._request_with_retry(
                "GET", f"/admin/clients/{client_id}"
            )

            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            else:
                error_text = await response.text()
                raise ValueError(f"Failed to get OAuth client: {error_text}")

        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return None
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get OAuth client: {e}")
            raise

    async def list_oauth_clients(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List OAuth2 clients.

        Args:
            limit: Maximum number of clients to return
            offset: Pagination offset

        Returns:
            List of OAuth2 clients
        """
        try:
            response = await self._request_with_retry(
                "GET", f"/admin/clients?limit={limit}&offset={offset}"
            )

            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to list OAuth clients: {error_text}")

            return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Failed to list OAuth clients: {e}")
            raise

    async def delete_oauth_client(self, client_id: str) -> bool:
        """Delete an OAuth2 client.

        Args:
            client_id: Client ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            response = await self._request_with_retry(
                "DELETE", f"/admin/clients/{client_id}"
            )

            if response.status in (200, 204):
                return True
            elif response.status == 404:
                return False
            else:
                error_text = await response.text()
                raise ValueError(f"Failed to delete OAuth client: {error_text}")

        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return False
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to delete OAuth client: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Hydra Admin API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._request_with_retry("GET", "/admin/health/ready")
            return response.status == 200
        except aiohttp.ClientError:
            return False

    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (JWKS) for token validation.

        Returns:
            JWKS data
        """
        try:
            response = await self._request_with_retry("GET", "/.well-known/jwks.json")

            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to get JWKS: {error_text}")

            return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Failed to get JWKS: {e}")
            raise

    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token.

        Args:
            token: Token to revoke

        Returns:
            True if revoked, False otherwise
        """
        data = {"token": token}

        try:
            response = await self._request_with_retry(
                "POST", "/admin/oauth2/revoke", data=data
            )

            return response.status in (200, 204)

        except aiohttp.ClientError as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
