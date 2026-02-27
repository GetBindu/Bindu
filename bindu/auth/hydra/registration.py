"""Hydra OAuth client registration utilities for agents.

This module provides utilities to automatically register agents as OAuth clients
in Ory Hydra during the bindufy process.
"""

from __future__ import annotations as _annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bindu.auth.hydra.client import HydraClient
from bindu.common.models import AgentCredentials
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_registration")


def save_agent_credentials(
    credentials: AgentCredentials, credentials_dir: Path
) -> None:
    """Save agent OAuth credentials to .bindu directory.

    Credentials are keyed by DID (client_id) instead of agent_id because
    agent_id changes on reload but DID remains stable.

    Args:
        credentials: Agent credentials to save
        credentials_dir: Directory to save credentials (typically .bindu)
    """
    credentials_dir.mkdir(exist_ok=True, parents=True)
    creds_file = credentials_dir / "oauth_credentials.json"

    # Load existing credentials if file exists
    existing_creds = {}
    if creds_file.exists():
        try:
            with open(creds_file, "r") as f:
                existing_creds = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing credentials: {e}")

    # Update with new credentials - use DID (client_id) as key for stability
    existing_creds[credentials.client_id] = credentials.to_dict()

    # Save to file
    with open(creds_file, "w") as f:
        json.dump(existing_creds, f, indent=2)

    # Set restrictive permissions (owner read/write only)
    creds_file.chmod(0o600)

    logger.info(f"✅ OAuth credentials saved to {creds_file}")
    logger.warning(f"⚠️  Keep {creds_file} secure and add to .gitignore!")


def load_agent_credentials(
    did: str, credentials_dir: Path
) -> Optional[AgentCredentials]:
    """Load agent OAuth credentials from .bindu directory.

    Credentials are looked up by DID (client_id) instead of agent_id because
    agent_id changes on reload but DID remains stable.

    Args:
        did: Agent DID (used as client_id)
        credentials_dir: Directory containing credentials

    Returns:
        AgentCredentials if found, None otherwise
    """
    creds_file = credentials_dir / "oauth_credentials.json"

    if not creds_file.exists():
        return None

    try:
        with open(creds_file, "r") as f:
            all_creds = json.load(f)

        # Look up by DID (client_id)
        if did not in all_creds:
            return None

        return AgentCredentials.from_dict(all_creds[did])
    except Exception as e:
        logger.error(f"Failed to load credentials for {did}: {e}")

    return None


async def register_agent_in_hydra(
    agent_id: str,
    agent_name: str,
    agent_url: str,
    did: str,
    credentials_dir: Path,
    did_extension=None,
) -> Optional[AgentCredentials]:
    """Register agent as OAuth client in Hydra using DID-based authentication.

    Args:
        agent_id: Unique agent identifier
        agent_name: Human-readable agent name
        agent_url: Agent's deployment URL
        did: Agent's DID
        credentials_dir: Directory to save credentials
        did_extension: DIDExtension instance for public key extraction (optional)

    Returns:
        AgentCredentials if successful, None otherwise
    """
    # Check if auto-registration is enabled
    if not app_settings.hydra.auto_register_agents:
        logger.info("Hydra auto-registration disabled, skipping")
        return None

    # Use DID as client_id for hybrid authentication
    client_id = did
    client_secret = secrets.token_urlsafe(32)

    # Create OAuth client in Hydra
    try:
        async with HydraClient(
            admin_url=app_settings.hydra.admin_url,
            public_url=app_settings.hydra.public_url,
            timeout=app_settings.hydra.timeout,
            verify_ssl=app_settings.hydra.verify_ssl,
            max_retries=app_settings.hydra.max_retries,
        ) as hydra:
            # Priority 1: Check Vault for existing credentials if enabled
            vault_creds = None
            if app_settings.vault.enabled:
                from bindu.utils.vault_client import VaultClient

                vault = VaultClient()
                try:
                    vault_creds = await vault.get_hydra_credentials(did)

                    if vault_creds:
                        logger.info(
                            f"✅ Found Hydra credentials in Vault for DID: {did}"
                        )

                        # Verify the client still exists in Hydra
                        existing_client = await hydra.get_oauth_client(
                            vault_creds.client_id
                        )
                        if existing_client:
                            logger.info(
                                f"✅ Hydra client verified in server: {vault_creds.client_id}"
                            )
                            # Save to local file as backup
                            save_agent_credentials(vault_creds, credentials_dir)
                            return vault_creds
                        else:
                            logger.warning(
                                "Vault credentials exist but client not found in Hydra. "
                                "Will recreate client with same credentials..."
                            )
                            # We'll recreate the client below using vault credentials
                            client_secret = vault_creds.client_secret
                finally:
                    await vault.close()

            # Priority 2: Check if client already exists in Hydra
            existing_client = await hydra.get_oauth_client(client_id)

            if existing_client:
                # Client exists in Hydra - check local credentials
                existing_creds = load_agent_credentials(did, credentials_dir)
                if existing_creds:
                    logger.info(f"OAuth credentials verified for DID: {did}")

                    # Backup to Vault if enabled and not already there
                    if app_settings.vault.enabled and not vault_creds:
                        from bindu.utils.vault_client import VaultClient

                        vault2 = VaultClient()
                        try:
                            await vault2.store_hydra_credentials(existing_creds)
                        finally:
                            await vault2.close()

                    return existing_creds
                elif vault_creds:
                    # We have vault creds and client exists, use vault creds
                    logger.info(
                        f"Using Vault credentials for existing Hydra client: {did}"
                    )
                    save_agent_credentials(vault_creds, credentials_dir)
                    return vault_creds
                else:
                    # Client exists in Hydra but no credentials anywhere - delete and recreate
                    logger.warning(
                        f"Client {client_id} exists in Hydra but no credentials found. "
                        "Deleting and recreating..."
                    )
                    await hydra.delete_oauth_client(client_id)
            else:
                # Client doesn't exist in Hydra
                if vault_creds:
                    # Use vault credentials to recreate client
                    logger.info(
                        f"Recreating Hydra client with Vault credentials for DID: {did}"
                    )
                    client_secret = vault_creds.client_secret
                else:
                    # Check if we have stale local credentials
                    existing_creds = load_agent_credentials(did, credentials_dir)
                    if existing_creds:
                        logger.warning(
                            f"Local credentials exist for {did} but client not found in Hydra. "
                            "Creating new client..."
                        )

            # Extract public key from DID extension if available
            public_key = None
            key_type = None
            if did_extension:
                try:
                    public_key = did_extension.public_key_base58
                    key_type = "Ed25519"
                    logger.info(
                        f"Extracted public key (base58) from DID extension for {did}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to extract public key from DID extension: {e}"
                    )

            # Create new OAuth client with DID metadata
            client_data = {
                "client_id": client_id,  # DID is the client_id
                "client_secret": client_secret,
                "client_name": agent_name,
                "grant_types": app_settings.hydra.default_grant_types,
                "response_types": ["code", "token"],
                "scope": " ".join(app_settings.hydra.default_agent_scopes),
                "token_endpoint_auth_method": "client_secret_post",
                "metadata": {
                    "agent_id": agent_id,
                    "agent_url": agent_url,
                    "did": did,
                    "public_key": public_key,
                    "key_type": key_type,
                    "verification_method": app_settings.did.verification_key_type
                    if key_type
                    else None,
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                    "hybrid_auth": True,  # Flag for hybrid OAuth2 + DID authentication
                },
            }

            await hydra.create_oauth_client(client_data)
            logger.info(f"✅ Agent registered in Hydra: {client_id}")

            # Create and save credentials
            credentials = AgentCredentials(
                agent_id=agent_id,
                client_id=client_id,
                client_secret=client_secret,
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=app_settings.hydra.default_agent_scopes,
            )

            # Save to local file
            save_agent_credentials(credentials, credentials_dir)

            # Backup to Vault if enabled
            if app_settings.vault.enabled:
                from bindu.utils.vault_client import VaultClient

                vault3 = VaultClient()
                try:
                    vault_stored = await vault3.store_hydra_credentials(credentials)
                    if vault_stored:
                        logger.info("✅ Hydra credentials backed up to Vault")
                    else:
                        logger.warning("⚠️  Failed to backup Hydra credentials to Vault")
                finally:
                    await vault3.close()

            return credentials

    except Exception as e:
        logger.error(f"Failed to register agent in Hydra: {e}")
        logger.warning(
            "Agent will start without OAuth credentials. "
            "Authentication may not work correctly."
        )
        return None
