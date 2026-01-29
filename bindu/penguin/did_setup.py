"""DID setup utilities for the penguin module.

This module handles DID extension initialization specific to agent creation.
It belongs in penguin (not utils) because it's domain-specific to agent setup.
"""

from pathlib import Path
from typing import Optional
from uuid import UUID

from bindu.extensions.did import DIDAgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.did_setup")


def initialize_did_extension(
    agent_id: str | UUID,
    author: Optional[str],
    agent_name: Optional[str],
    key_dir: Path,
    recreate_keys: bool = True,
    key_password: Optional[str] = None,
) -> DIDAgentExtension:
    """Initialize DID extension with key management.

    Args:
        agent_id: Unique agent identifier
        author: Agent author email
        agent_name: Human-readable agent name
        key_dir: Directory for storing DID keys
        recreate_keys: Force regeneration of existing keys
        key_password: Optional password for key encryption

    Returns:
        Initialized DIDAgentExtension instance

    Raises:
        Exception: If DID initialization fails
    """
    try:
        logger.info(f"Initializing DID extension for agent: {agent_name}")

        # Create DID extension
        did_extension = DIDAgentExtension(
            recreate_keys=recreate_keys,
            key_dir=key_dir / app_settings.did.pki_dir,
            author=author,
            agent_name=agent_name,
            agent_id=str(agent_id),
            key_password=key_password,
        )

        # Generate and save key pair
        did_extension.generate_and_save_key_pair()

        logger.info(f"DID extension initialized successfully: {did_extension.did}")
        return did_extension

    except Exception as exc:
        logger.error(f"Failed to initialize DID extension: {exc}")
        raise
