"""HashiCorp Vault client for storing DID keys and Hydra credentials.

This module provides a client for storing and retrieving sensitive agent data
from HashiCorp Vault, ensuring persistence across pod restarts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from bindu.common.models import AgentCredentials
from bindu.settings import app_settings
from bindu.utils.http_client import AsyncHTTPClient
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.vault_client")


class VaultClient:
    """Client for interacting with HashiCorp Vault.

    Stores and retrieves DID keys and Hydra OAuth credentials to ensure
    agent identity persistence across pod restarts.
    """

    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
    ) -> None:
        """Initialize Vault client.

        Args:
            vault_url: Vault server URL (defaults to app_settings.vault.url)
            vault_token: Vault authentication token (defaults to app_settings.vault.token)
        """
        self.vault_url = (vault_url or app_settings.vault.url).rstrip("/")
        self.vault_token = vault_token or app_settings.vault.token
        self.enabled = app_settings.vault.enabled and bool(self.vault_token)

        if not self.enabled:
            logger.debug("Vault client disabled or not configured")
        else:
            logger.info(f"Vault client initialized: {self.vault_url}")

        # Initialize HTTP client with Vault-specific headers
        self._http_client = AsyncHTTPClient(
            base_url=self.vault_url,
            timeout=10,
            verify_ssl=True,
            max_retries=3,
            default_headers={
                "X-Vault-Token": self.vault_token,
                "Content-Type": "application/json",
            },
        )

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
    ) -> Optional[dict[str, Any]]:
        """Make HTTP request to Vault API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /v1/secret/data/my-secret)
            data: Optional request body

        Returns:
            Response JSON or None if request fails
        """
        if not self.enabled:
            logger.warning("Vault client not enabled, skipping request")
            return None

        try:
            response = await self._http_client.request(
                method,
                path,
                json=data,
            )

            if response.status == 404:
                logger.error(
                    f"Vault path not found (404): {path}. "
                    f"Ensure KV v2 secrets engine is enabled at 'secret' mount: "
                    f"'vault secrets enable -path=secret kv-v2'"
                )
                return None

            if response.status >= 400:
                error_text = await response.text()
                logger.error(
                    f"Vault request failed: {method} {path} - "
                    f"Status: {response.status} - Response: {error_text}"
                )
                return None

            return await response.json()

        except Exception as e:
            logger.error(f"Vault request error: {e}")
            return None

    async def close(self) -> None:
        """Close the HTTP client session."""
        await self._http_client.close()

    async def store_did_keys(
        self,
        agent_id: str,
        private_key_pem: str,
        public_key_pem: str,
        did: str,
    ) -> bool:
        """Store DID keys in Vault.

        Args:
            agent_id: Unique agent identifier
            private_key_pem: PEM-encoded private key
            public_key_pem: PEM-encoded public key
            did: Agent's DID

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping DID key storage")
            return False

        path = f"/v1/secret/data/bindu/agents/{agent_id}/did-keys"
        data = {
            "data": {
                "private_key": private_key_pem,
                "public_key": public_key_pem,
                "did": did,
            }
        }

        result = await self._make_request("POST", path, data)
        if result:
            logger.info(f"✅ DID keys stored in Vault for agent: {agent_id}")
            return True
        else:
            logger.error(
                f"Failed to store DID keys in Vault for agent: {agent_id}. "
                f"Check Vault permissions and KV v2 engine at 'secret' mount."
            )
            return False

    async def get_did_keys(self, agent_id: str) -> Optional[dict[str, str]]:
        """Retrieve DID keys from Vault.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Dictionary with 'private_key', 'public_key', 'did' or None if not found
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping DID key retrieval")
            return None

        path = f"/v1/secret/data/bindu/agents/{agent_id}/did-keys"
        result = await self._make_request("GET", path)

        if result and "data" in result and "data" in result["data"]:
            keys = result["data"]["data"]
            logger.info(f"✅ DID keys retrieved from Vault for agent: {agent_id}")
            return {
                "private_key": keys.get("private_key"),
                "public_key": keys.get("public_key"),
                "did": keys.get("did"),
            }

        logger.debug(f"No DID keys found in Vault for agent: {agent_id}")
        return None

    async def store_hydra_credentials(
        self,
        credentials: AgentCredentials,
    ) -> bool:
        """Store Hydra OAuth credentials in Vault.

        Args:
            credentials: Agent credentials to store

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping Hydra credential storage")
            return False

        # Use DID (client_id) as the key for stability
        path = f"/v1/secret/data/bindu/hydra/credentials/{credentials.client_id}"
        data = {"data": credentials.to_dict()}

        result = await self._make_request("POST", path, data)
        if result:
            logger.info(
                f"✅ Hydra credentials stored in Vault for DID: {credentials.client_id}"
            )
            return True
        else:
            logger.error(
                f"Failed to store Hydra credentials in Vault for DID: {credentials.client_id}"
            )
            return False

    async def get_hydra_credentials(
        self,
        did: str,
    ) -> Optional[AgentCredentials]:
        """Retrieve Hydra OAuth credentials from Vault.

        Args:
            did: Agent's DID (used as client_id)

        Returns:
            AgentCredentials if found, None otherwise
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping Hydra credential retrieval")
            return None

        path = f"/v1/secret/data/bindu/hydra/credentials/{did}"
        result = await self._make_request("GET", path)

        if result and "data" in result and "data" in result["data"]:
            creds_data = result["data"]["data"]
            logger.info(f"✅ Hydra credentials retrieved from Vault for DID: {did}")
            return AgentCredentials.from_dict(creds_data)

        logger.debug(f"No Hydra credentials found in Vault for DID: {did}")
        return None

    async def delete_did_keys(self, agent_id: str) -> bool:
        """Delete DID keys from Vault.

        Args:
            agent_id: Unique agent identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping DID key deletion")
            return False

        path = f"/v1/secret/metadata/bindu/agents/{agent_id}/did-keys"
        result = await self._make_request("DELETE", path)

        if result is not None:
            logger.info(f"✅ DID keys deleted from Vault for agent: {agent_id}")
            return True
        else:
            logger.error(f"Failed to delete DID keys from Vault for agent: {agent_id}")
            return False

    async def delete_hydra_credentials(self, did: str) -> bool:
        """Delete Hydra credentials from Vault.

        Args:
            did: Agent's DID (used as client_id)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Vault disabled, skipping Hydra credential deletion")
            return False

        path = f"/v1/secret/metadata/bindu/hydra/credentials/{did}"
        result = await self._make_request("DELETE", path)

        if result is not None:
            logger.info(f"✅ Hydra credentials deleted from Vault for DID: {did}")
            return True
        else:
            logger.error(
                f"Failed to delete Hydra credentials from Vault for DID: {did}"
            )
            return False


async def restore_did_keys_from_vault(
    agent_id: str,
    key_dir: Path,
) -> Optional[str]:
    """Restore DID keys from Vault to local filesystem.

    Args:
        agent_id: Unique agent identifier
        key_dir: Directory to restore keys to

    Returns:
        DID if successful, None otherwise
    """
    vault = VaultClient()
    try:
        keys = await vault.get_did_keys(agent_id)

        if not keys:
            return None

        # Create key directory if it doesn't exist
        key_dir.mkdir(parents=True, exist_ok=True)

        # Write private key using filename from settings
        private_key_path = key_dir / app_settings.did.private_key_filename
        with open(private_key_path, "w") as f:
            f.write(keys["private_key"])
        private_key_path.chmod(0o600)

        # Write public key using filename from settings
        public_key_path = key_dir / app_settings.did.public_key_filename
        with open(public_key_path, "w") as f:
            f.write(keys["public_key"])
        public_key_path.chmod(0o644)

        logger.info(f"✅ DID keys restored from Vault to {key_dir}")
        return keys["did"]

    except Exception as e:
        logger.error(f"Failed to restore DID keys from Vault: {e}")
        return None
    finally:
        await vault.close()


async def backup_did_keys_to_vault(
    agent_id: str,
    key_dir: Path,
    did: str,
) -> bool:
    """Backup DID keys from local filesystem to Vault.

    Args:
        agent_id: Unique agent identifier
        key_dir: Directory containing keys
        did: Agent's DID

    Returns:
        True if successful, False otherwise
    """
    vault = VaultClient()
    try:
        # Read private key using filename from settings
        private_key_path = key_dir / app_settings.did.private_key_filename
        if not private_key_path.exists():
            logger.error(f"Private key not found at {private_key_path}")
            return False

        with open(private_key_path, "r") as f:
            private_key_pem = f.read()

        # Read public key using filename from settings
        public_key_path = key_dir / app_settings.did.public_key_filename
        if not public_key_path.exists():
            logger.error(f"Public key not found at {public_key_path}")
            return False

        with open(public_key_path, "r") as f:
            public_key_pem = f.read()

        # Store in Vault
        return await vault.store_did_keys(
            agent_id=agent_id,
            private_key_pem=private_key_pem,
            public_key_pem=public_key_pem,
            did=did,
        )

    except Exception as e:
        logger.error(f"Failed to backup DID keys to Vault: {e}")
        return False
    finally:
        await vault.close()
