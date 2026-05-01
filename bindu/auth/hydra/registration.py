"""Hydra OAuth client registration utilities for agents.

This module provides utilities to automatically register agents as OAuth clients
in Ory Hydra during the bindufy process.
"""

from __future__ import annotations as _annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from bindu.auth.hydra.client import HydraClient
from bindu.common.models import AgentCredentials
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_registration")


def save_agent_credentials(
    credentials: AgentCredentials, credentials_dir: Path
) -> None:
    """Save agent OAuth credentials to .GetBindu.com."""
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

    # Update credentials
    existing_creds[credentials.client_id] = credentials.to_dict()

    # ✅ SIMPLE + CORRECT WRITE
    with open(creds_file, "w") as f:
        json.dump(existing_creds, f, indent=2)

    # 🔐 FORCE PERMISSIONS (this is the only addition)
    try:
        os.chmod(creds_file, 0o600)
    except Exception:
        pass

    logger.info(f"✅ OAuth credentials saved to {creds_file}")
    logger.warning(f"⚠️  Keep {creds_file} secure and add to .gitignore!")


def load_agent_credentials(
    did: str, credentials_dir: Path
) -> Optional[AgentCredentials]:
    """Load agent OAuth credentials from .GetBindu.com."""
    creds_file = credentials_dir / "oauth_credentials.json"

    if not creds_file.exists():
        return None

    try:
        with open(creds_file, "r") as f:
            all_creds = json.load(f)

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
    did_extension: Optional[Any] = None,
) -> Optional[AgentCredentials]:
    """Register agent as OAuth client in Hydra using DID-based authentication."""
    if not app_settings.hydra.auto_register_agents:
        logger.info("Hydra auto-registration disabled, skipping")
        return None
    client_id = did
    client_secret = secrets.token_urlsafe(32)
    vault_client = None
    try:
        if app_settings.vault.enabled:
            from bindu.utils.http.vault_client import VaultClient

            vault_client = VaultClient()

        async with HydraClient(
            admin_url=app_settings.hydra.admin_url,
            public_url=app_settings.hydra.public_url,
            timeout=app_settings.hydra.timeout,
            verify_ssl=app_settings.hydra.verify_ssl,
            max_retries=app_settings.hydra.max_retries,
        ) as hydra:
            vault_creds = None
            if vault_client:
                try:
                    vault_creds = await vault_client.get_hydra_credentials(did)

                    if vault_creds:
                        logger.info(
                            f"✅ Found Hydra credentials in Vault for DID: {did}"
                        )

                        existing_client = await hydra.get_oauth_client(
                            vault_creds.client_id
                        )
                        if existing_client:
                            save_agent_credentials(vault_creds, credentials_dir)
                            return vault_creds
                        else:
                            client_secret = vault_creds.client_secret
                except Exception as e:
                    logger.warning(f"Failed to get credentials from Vault: {e}")

            existing_client = await hydra.get_oauth_client(client_id)

            if existing_client:
                existing_creds = load_agent_credentials(did, credentials_dir)
                if existing_creds:
                    return existing_creds
                elif vault_creds:
                    save_agent_credentials(vault_creds, credentials_dir)
                    return vault_creds
                else:
                    await hydra.delete_oauth_client(client_id)

            public_key = None
            key_type = None
            if did_extension:
                try:
                    public_key = did_extension.public_key_base58
                    key_type = "Ed25519"
                except Exception:
                    pass

            client_data = {
                "client_id": client_id,
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
                    "hybrid_auth": True,
                },
            }

            await hydra.create_oauth_client(client_data)

            credentials = AgentCredentials(
                agent_id=agent_id,
                client_id=client_id,
                client_secret=client_secret,
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=app_settings.hydra.default_agent_scopes,
            )

            save_agent_credentials(credentials, credentials_dir)

            if vault_client:
                try:
                    await vault_client.store_hydra_credentials(credentials)
                except Exception:
                    pass

            return credentials

    except Exception as e:
        logger.error(f"Failed to register agent in Hydra: {e}")
        return None
    finally:
        if vault_client:
            await vault_client.close()
