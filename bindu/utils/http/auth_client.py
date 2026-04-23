"""Client utilities for making requests with hybrid OAuth2 + DID authentication.

This module provides helper functions for clients to easily make authenticated
requests using both OAuth2 tokens and DID signatures.
"""

from __future__ import annotations as _annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bindu.utils.did import sign_request
from .client import AsyncHTTPClient
from bindu.utils.logging import get_logger
from .tokens import get_client_credentials_token

logger = get_logger("bindu.utils.hybrid_auth_client")


class HybridAuthClient:
    """Client for making authenticated requests with OAuth2 + DID signatures.

    This client handles:
    - Getting OAuth2 tokens from Hydra
    - Signing requests with DID private key
    - Making HTTP requests with both authentication layers
    """

    def __init__(
        self,
        agent_id: str,
        credentials_dir: Path,
        did_extension,
    ):
        """Initialize hybrid auth client.

        Args:
            agent_id: Agent identifier
            credentials_dir: Directory containing oauth_credentials.json
            did_extension: DIDExtension instance with private key
        """
        self.agent_id = agent_id
        self.credentials_dir = credentials_dir
        self.did_extension = did_extension
        self.credentials = None
        self.access_token = None

    async def initialize(self):
        """Load credentials and get initial access token."""
        # Import here to avoid circular dependency:
        # auth_client -> registration -> HydraClient -> AsyncHTTPClient -> auth_client
        from bindu.auth.hydra.registration import load_agent_credentials

        # Load OAuth credentials
        self.credentials = load_agent_credentials(self.agent_id, self.credentials_dir)
        if not self.credentials:
            raise ValueError(f"No credentials found for agent: {self.agent_id}")

        # Get access token
        await self.refresh_token()

    async def refresh_token(self):
        """Get a new access token from Hydra."""
        # Type narrowing: credentials is guaranteed to be set after initialize()
        assert self.credentials is not None
        scope = " ".join(self.credentials.scopes)
        token_response = await get_client_credentials_token(
            self.credentials.client_id,
            self.credentials.client_secret,
            scope,
        )

        if not token_response:
            raise Exception("Failed to get access token")

        self.access_token = token_response["access_token"]
        logger.info(f"Access token obtained for {self.credentials.client_id}")

    def _create_signed_request_headers(self, body: str | bytes) -> Dict[str, str]:
        """Create complete headers for signed request with OAuth token.

        Args:
            body: Request body — must be a str or bytes (dict no longer
                accepted, see bindu.utils.did.sign_request for the
                contract).

        Returns:
            Dict with all required headers
        """
        assert self.credentials is not None
        assert self.access_token is not None

        # Get DID signature headers
        signature_headers = sign_request(
            body, self.credentials.client_id, self.did_extension
        )

        # Combine with OAuth token
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            **signature_headers,
        }

    async def post(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated POST request with hybrid authentication.

        Args:
            url: Target URL
            data: Request body (will be JSON encoded)
            headers: Additional headers (optional)

        Returns:
            Response JSON
        """
        # Refresh token if needed
        if not self.access_token:
            await self.refresh_token()

        # Type narrowing: credentials and access_token are set after initialize()
        assert self.credentials is not None
        assert self.access_token is not None

        # Parse URL to get base and path
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"

        # Create signed request headers
        body_str = json.dumps(data)
        auth_headers = self._create_signed_request_headers(body_str)

        # Merge with additional headers
        if headers:
            auth_headers.update(headers)

        # Make request
        async with AsyncHTTPClient(base_url=base_url) as client:
            response = await client.post(path, headers=auth_headers, json=data)

            if response.status == 401:
                # Token might be expired, refresh and retry
                logger.info("Token expired, refreshing...")
                await self.refresh_token()

                # Update headers with new token
                auth_headers = self._create_signed_request_headers(body_str)
                if headers:
                    auth_headers.update(headers)

                # Retry request
                response = await client.post(path, headers=auth_headers, json=data)

            return await response.json()

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated GET request with hybrid authentication.

        Args:
            url: Full URL to make request to
            headers: Optional additional headers

        Returns:
            Response JSON
        """
        # Refresh token if needed
        if not self.access_token:
            await self.refresh_token()

        # Type narrowing: credentials and access_token are set after initialize()
        assert self.credentials is not None
        assert self.access_token is not None

        # Parse URL to get base and path
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"

        # Create signed request headers (empty body for GET)
        auth_headers = self._create_signed_request_headers("")

        # Merge with additional headers
        if headers:
            auth_headers.update(headers)

        # Make request
        async with AsyncHTTPClient(base_url=base_url) as client:
            response = await client.get(path, headers=auth_headers)

            if response.status == 401:
                # Token might be expired, refresh and retry
                logger.info("Token expired, refreshing...")
                await self.refresh_token()

                auth_headers["Authorization"] = f"Bearer {self.access_token}"
                response = await client.get(path, headers=auth_headers)

            return await response.json()
