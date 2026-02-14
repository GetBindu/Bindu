"""Token management utilities for Hydra authentication.

This module provides helper functions for managing OAuth tokens,
including getting tokens for agents and validating tokens.
"""

from __future__ import annotations as _annotations

from typing import Optional

from bindu.auth.hydra.registration import load_agent_credentials
from bindu.settings import app_settings
from bindu.utils.http_client import http_client
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.token_utils")


async def get_client_credentials_token(
    client_id: str, client_secret: str, scope: Optional[str] = None
) -> Optional[dict]:
    """Get access token using client credentials grant.

    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        scope: Optional space-separated scopes

    Returns:
        Token response dict with access_token, token_type, expires_in
    """
    try:
        # Use client_secret_post (credentials in body) instead of client_secret_basic
        # because DIDs contain colons which break HTTP Basic auth
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        if scope:
            data["scope"] = scope

        async with http_client(
            base_url=app_settings.hydra.public_url,
            verify_ssl=app_settings.hydra.verify_ssl,
            timeout=app_settings.hydra.timeout,
        ) as client:
            response = await client.post("/oauth2/token", headers=headers, data=data)

            if response.status == 200:
                result = await response.json()
                logger.debug(f"Token obtained for client: {client_id}")
                return result
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to get token for {client_id}: {response.status} - {error_text}"
                )
                return None

    except Exception as e:
        logger.error(f"Failed to get client credentials token: {e}")
        return None


async def get_agent_token_from_credentials_file(
    agent_id: str, credentials_dir
) -> Optional[str]:
    """Get access token for agent from saved credentials.

    Args:
        agent_id: Agent identifier
        credentials_dir: Directory containing oauth_credentials.json

    Returns:
        Access token string or None
    """
    # Load credentials from file
    credentials = load_agent_credentials(agent_id, credentials_dir)
    if not credentials:
        logger.error(f"No credentials found for agent: {agent_id}")
        return None

    # Get token
    scope = " ".join(credentials.scopes)
    token_response = await get_client_credentials_token(
        credentials.client_id, credentials.client_secret, scope
    )

    if token_response:
        return token_response.get("access_token")

    return None


async def introspect_token(token: str) -> Optional[dict]:
    """Introspect a token to check if it's valid.

    Args:
        token: Access token to introspect

    Returns:
        Introspection result dict or None
    """
    from bindu.auth.hydra.client import HydraClient

    try:
        async with HydraClient(
            admin_url=app_settings.hydra.admin_url,
            public_url=app_settings.hydra.public_url,
            timeout=app_settings.hydra.timeout,
            verify_ssl=app_settings.hydra.verify_ssl,
        ) as hydra:
            result = await hydra.introspect_token(token)
            return result

    except Exception as e:
        logger.error(f"Failed to introspect token: {e}")
        return None


async def revoke_token(token: str) -> bool:
    """Revoke an access or refresh token.

    Args:
        token: Token to revoke

    Returns:
        True if revoked successfully, False otherwise
    """
    from bindu.auth.hydra.client import HydraClient

    try:
        async with HydraClient(
            admin_url=app_settings.hydra.admin_url,
            public_url=app_settings.hydra.public_url,
            timeout=app_settings.hydra.timeout,
            verify_ssl=app_settings.hydra.verify_ssl,
        ) as hydra:
            return await hydra.revoke_token(token)

    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


def create_bearer_header(token: str) -> dict:
    """Create Authorization header with Bearer token.

    Args:
        token: Access token

    Returns:
        Dict with Authorization header
    """
    return {"Authorization": f"Bearer {token}"}


async def validate_token_and_get_subject(token: str) -> Optional[str]:
    """Validate token and extract subject (user/client ID).

    Args:
        token: Access token

    Returns:
        Subject (sub claim) if valid, None otherwise
    """
    result = await introspect_token(token)

    if result and result.get("active"):
        return result.get("sub")

    return None
