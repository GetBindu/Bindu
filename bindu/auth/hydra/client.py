"""Hydra API client for token introspection and OAuth2 management.

This client handles communication with Ory Hydra's Admin API for token operations.
"""

from __future__ import annotations as _annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from bindu.utils.http import AsyncHTTPClient
from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_client")

# Default Hydra ports
DEFAULT_ADMIN_PORT = 4445
DEFAULT_PUBLIC_PORT = 4444


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
            public_url.rstrip("/")
            if public_url
            else admin_url.replace(str(DEFAULT_ADMIN_PORT), str(DEFAULT_PUBLIC_PORT))
        )

        # Use the reusable HTTP client
        self._http_client = AsyncHTTPClient(
            base_url=self.admin_url,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            default_headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        logger.debug(
            f"Hydra client initialized: admin={admin_url}, public={self.public_url}"
        )

    async def __aenter__(self) -> "HydraClient":
        """Async context manager entry."""
        await self._http_client._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client session."""
        await self._http_client.close()

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """Introspect OAuth2 token using Hydra Admin API.

        Args:
            token: OAuth2 access token

        Returns:
            Token introspection result

        Raises:
            ValueError: If token introspection fails
        """
        data = {
            "token": token,
            "scope": "",  # Optional: specify required scopes
        }

        try:
            response = await self._http_client.post(
                "/admin/oauth2/introspect", data=data
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

        except Exception as error:
            logger.error(f"Error during token introspection: {error}")
            raise ValueError(f"Failed to introspect token: {str(error)}") from error

    async def create_oauth_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new OAuth2 client in Hydra.

        Args:
            client_data: OAuth2 client configuration

        Returns:
            Created client information
        """
        try:
            response = await self._http_client.post("/admin/clients", json=client_data)

            if response.status not in (200, 201):
                error_text = await response.text()
                raise ValueError(f"Failed to create OAuth client: {error_text}")

            return await response.json()

        except Exception as error:
            logger.error(f"Failed to create OAuth client: {error}")
            raise

    async def get_oauth_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth2 client information.

        Args:
            client_id: Client ID to retrieve

        Returns:
            Client information or None if not found
        """
        from bindu.utils.exceptions import HTTPClientError

        try:
            # URL-encode client_id to handle DIDs with colons and special characters
            encoded_client_id = quote(client_id, safe="")
            response = await self._http_client.get(
                f"/admin/clients/{encoded_client_id}"
            )

            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            else:
                error_text = await response.text()
                raise ValueError(f"Failed to get OAuth client: {error_text}")

        except HTTPClientError as error:
            # AsyncHTTPClient raises HTTPClientError for 4xx errors including 404
            if error.status == 404:
                logger.debug(f"OAuth client not found: {client_id}")
                return None
            # Re-raise other client errors
            logger.error(f"Failed to get OAuth client: {error}")
            raise
        except Exception as error:
            # Other errors (connection, timeout, etc.)
            logger.error(f"Failed to get OAuth client: {error}")
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
            response = await self._http_client.get(
                f"/admin/clients?limit={limit}&offset={offset}"
            )

            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to list OAuth clients: {error_text}")

            return await response.json()

        except Exception as error:
            logger.error(f"Failed to list OAuth clients: {error}")
            raise

    async def delete_oauth_client(self, client_id: str) -> bool:
        """Delete an OAuth2 client.

        Args:
            client_id: Client ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # URL-encode client_id to handle DIDs with colons and special characters
            encoded_client_id = quote(client_id, safe="")
            response = await self._http_client.delete(
                f"/admin/clients/{encoded_client_id}"
            )

            if response.status in (200, 204):
                return True
            elif response.status == 404:
                return False
            else:
                error_text = await response.text()
                raise ValueError(f"Failed to delete OAuth client: {error_text}")

        except Exception as error:
            # AsyncHTTPClient raises HTTPClientError for 404s
            # If we get here, it's a different error
            logger.error(f"Failed to delete OAuth client: {error}")
            raise

    async def health_check(self) -> bool:
        """Check if Hydra Admin API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._http_client.get("/admin/health/ready")
            return response.status == 200
        except Exception as error:
            logger.warning(f"Hydra health check failed: {error}")
            return False

    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (JWKS) for token validation.

        Returns:
            JWKS data
        """
        try:
            response = await self._http_client.get("/.well-known/jwks.json")

            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to get JWKS: {error_text}")

            return await response.json()

        except Exception as error:
            logger.error(f"Failed to get JWKS: {error}")
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
            response = await self._http_client.post("/admin/oauth2/revoke", data=data)
            return response.status in (200, 204)

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            raise

    async def get_public_key_from_client(self, client_did: str) -> Optional[str]:
        """Get client's public key from Hydra metadata.

        Args:
            client_did: Client's DID (used as client_id)

        Returns:
            Public key (multibase encoded) or None
        """
        try:
            client = await self.get_oauth_client(client_did)
            if not client:
                logger.error(f"Client not found in Hydra: {client_did}")
                return None

            public_key = client.get("metadata", {}).get("public_key")
            if not public_key:
                logger.warning(f"No public key found for client: {client_did}")
                return None

            return public_key

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Data error getting public key from Hydra: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting public key from Hydra: {e}")
            return None
