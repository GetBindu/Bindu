"""Hydra API client for token introspection and OAuth2 management.

This client handles communication with Ory Hydra's Admin API for token operations.
"""

from __future__ import annotations as _annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from bindu.utils.http_client import AsyncHTTPClient
from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_client")


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

        except Exception as e:
            logger.error(f"Error during token introspection: {e}")
            raise ValueError(f"Failed to introspect token: {str(e)}")

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

        except Exception as e:
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

        except Exception as e:
            if hasattr(e, "status") and e.status == 404:
                return None
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
            response = await self._http_client.get(
                f"/admin/clients?limit={limit}&offset={offset}"
            )

            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to list OAuth clients: {error_text}")

            return await response.json()

        except Exception as e:
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

        except Exception as e:
            if hasattr(e, "status") and e.status == 404:
                return False
            logger.error(f"Failed to delete OAuth client: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Hydra Admin API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._http_client.get("/admin/health/ready")
            return response.status == 200
        except Exception:
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

        except Exception as e:
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
            response = await self._http_client.post("/admin/oauth2/revoke", data=data)

            return response.status in (200, 204)

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def update_client_certificate(self, client_id: str, x509_cert: str) -> bool:
        """Bind an x509 certificate to an OAuth2 client for mTLS authentication.

        Args:
            client_id: OAuth2 Client ID (DID)
            x509_cert: PEM encoded certificate string

        Returns:
            True if successful
        """
        try:
            # Fetch existing client first to avoid overwriting other fields
            client = await self.get_oauth_client(client_id)
            if not client:
                raise ValueError(f"Client {client_id} not found")

            # Update client with TLS settings
            # We use 'tls_client_auth' or 'self_signed_tls_client_auth'
            client["token_endpoint_auth_method"] = "self_signed_tls_client_auth"

            # Helper to extract the public key from the cert if needed,
            # but Hydra usually takes the JWKS.
            # For self-signed, we might need to add it to the JWKS of the client.

            # NOTE: Hydra supports mutual TLS for client authentication.
            # If we want to strictly use mTLS (not private_key_jwt), we usually enforce
            # it at the ingress or configure Hydra to check the client cert.
            # For 'self_signed_tls_client_auth', we usually need to register the
            # cert's public key in the client's JWKS.

            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
            import base64

            # Load cert to get public key
            cert = x509.load_pem_x509_certificate(x509_cert.encode())
            public_key = cert.public_key()

            # Convert to JWK (simplified for RSA)
            from cryptography.hazmat.primitives.asymmetric import rsa

            if isinstance(public_key, rsa.RSAPublicKey):
                numbers = public_key.public_numbers()
                jwk = {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": str(cert.serial_number),
                    "n": base64.urlsafe_b64encode(
                        numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
                    )
                    .decode("utf-8")
                    .rstrip("="),
                    "e": base64.urlsafe_b64encode(
                        numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
                    )
                    .decode("utf-8")
                    .rstrip("="),
                    "x5c": [
                        base64.b64encode(
                            cert.public_bytes(serialization.Encoding.DER)
                        ).decode("utf-8")
                    ],
                }

                client["jwks"] = {"keys": [jwk]}

            # Update the client
            encoded_client_id = quote(client_id, safe="")
            response = await self._http_client.put(
                f"/admin/clients/{encoded_client_id}", json=client
            )

            if response.status not in (200, 201):
                error_text = await response.text()
                logger.error(f"Failed to update client certificate: {error_text}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to bind certificate to client: {e}")
            return False
