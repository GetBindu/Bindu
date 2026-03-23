"""DID setup utilities for the penguin module.

This module handles DID extension initialization specific to agent creation.
It belongs in penguin (not utils) because it's domain-specific to agent setup.
"""

import asyncio
from pathlib import Path
from typing import Optional
from uuid import UUID

from bindu.extensions.did import DIDAgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.did_setup")


def _restore_keys_from_vault(agent_id_str: str, pki_dir: Path) -> Optional[str]:
    """Restore DID keys from Vault if available.

    Args:
        agent_id_str: Agent ID as string
        pki_dir: Directory where keys should be restored

    Returns:
        Restored DID if successful, None otherwise
    """
    from bindu.utils.http.vault_client import restore_did_keys_from_vault

    logger.info(f"Attempting to restore DID keys from Vault for agent: {agent_id_str}")
    restored_did = asyncio.run(
        restore_did_keys_from_vault(agent_id=agent_id_str, key_dir=pki_dir)
    )

    if restored_did:
        logger.info(f"✅ DID keys restored from Vault: {restored_did}")
    else:
        logger.info("No existing DID keys found in Vault, will generate new keys")

    return restored_did


def _backup_keys_to_vault(agent_id_str: str, pki_dir: Path, did: str) -> bool:
    """Backup DID keys to Vault.

    Args:
        agent_id_str: Agent ID as string
        pki_dir: Directory containing keys to backup
        did: DID identifier

    Returns:
        True if backup successful, False otherwise
    """
    from bindu.utils.http.vault_client import backup_did_keys_to_vault

    logger.info(f"Backing up DID keys to Vault for agent: {agent_id_str}")
    backup_success = asyncio.run(
        backup_did_keys_to_vault(agent_id=agent_id_str, key_dir=pki_dir, did=did)
    )

    if backup_success:
        logger.info("✅ DID keys backed up to Vault")
    else:
        logger.warning("⚠️  Failed to backup DID keys to Vault")

    return backup_success


def initialize_did_extension(
    agent_id: str | UUID,
    author: Optional[str],
    agent_name: Optional[str],
    key_dir: Path,
    recreate_keys: bool = False,
    key_password: Optional[str] = None,
) -> DIDAgentExtension:
    """Initialize DID extension with key management.

    Args:
        agent_id: Unique agent identifier
        author: Agent author email
        agent_name: Human-readable agent name
        key_dir: Directory for storing DID keys
        recreate_keys: Force regeneration of existing keys (default: False)
        key_password: Optional password for key encryption

    Returns:
        Initialized DIDAgentExtension instance

    Raises:
        Exception: If DID initialization fails
    """
    try:
        logger.info(f"Initializing DID extension for agent: {agent_name}")

        # Convert agent_id to string once
        agent_id_str = str(agent_id)
        pki_dir = key_dir / app_settings.did.pki_dir

        # Try to restore DID keys from Vault if enabled and keys don't exist locally
        if app_settings.vault.enabled and not recreate_keys:
            # Check if keys already exist locally using settings constants
            private_key_exists = (
                pki_dir / app_settings.did.private_key_filename
            ).exists()
            public_key_exists = (
                pki_dir / app_settings.did.public_key_filename
            ).exists()

            if not (private_key_exists and public_key_exists):
                _restore_keys_from_vault(agent_id_str, pki_dir)

        # Create DID extension
        did_extension = DIDAgentExtension(
            recreate_keys=recreate_keys,
            key_dir=pki_dir,
            author=author,
            agent_name=agent_name,
            agent_id=agent_id_str,
            key_password=key_password,
        )

        # Generate and save key pair (will skip if keys already exist and recreate_keys=False)
        did_extension.generate_and_save_key_pair()

        # Perform integrity checks after keys are available
        try:
            did_extension.check_integrity()
            logger.info("✅ DID configuration and keys pass integrity check")
        except ValueError as e:
            logger.error(f"❌ DID integrity check failed: {e}")
            # Raise to enforce security - DID integrity is critical for agent identity
            raise

        # Backup keys to Vault if enabled
        if app_settings.vault.enabled:
            _backup_keys_to_vault(agent_id_str, pki_dir, did_extension.did)

        logger.info(f"DID extension initialized successfully: {did_extension.did}")
        return did_extension

    except Exception as exc:
        logger.error(f"Failed to initialize DID extension: {exc}")
        raise
