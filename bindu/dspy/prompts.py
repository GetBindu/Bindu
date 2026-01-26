# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Prompt management for DSPy agents with A/B testing support.

This module provides high-level functions for managing agent prompts,
using the centralized storage layer for all database operations.
"""

from __future__ import annotations

from typing import Any

from bindu.server.storage.postgres_storage import PostgresStorage


async def _get_storage(did: str | None = None) -> PostgresStorage:
    """Get a storage instance for prompt operations with DID isolation.
    
    Args:
        did: Decentralized Identifier for schema isolation
    
    Returns:
        Initialized PostgresStorage instance configured for the specified DID schema
    """
    storage = PostgresStorage(did=did)
    await storage.connect()
    return storage


async def get_active_prompt(did: str | None = None) -> dict[str, Any] | None:
    """Get the current active prompt.
    
    Args:
        did: Decentralized Identifier for schema isolation
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no active prompt exists
    """
    storage = await _get_storage(did=did)
    try:
        return await storage.get_active_prompt()
    finally:
        await storage.disconnect()


async def get_candidate_prompt(did: str | None = None) -> dict[str, Any] | None:
    """Get the current candidate prompt.
    
    Args:
        did: Decentralized Identifier for schema isolation
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no candidate prompt exists
    """
    storage = await _get_storage(did=did)
    try:
        return await storage.get_candidate_prompt()
    finally:
        await storage.disconnect()


async def insert_prompt(text: str, status: str, traffic: float, did: str | None = None) -> int:
    """Insert a new prompt into the database.
    
    Args:
        text: The prompt text content
        status: The prompt status (active, candidate, deprecated, rolled_back)
        traffic: Traffic allocation (0.0 to 1.0)
        did: Decentralized Identifier for schema isolation
        
    Returns:
        The ID of the newly inserted prompt
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    storage = await _get_storage(did=did)
    try:
        return await storage.insert_prompt(text, status, traffic)
    finally:
        await storage.disconnect()


async def update_prompt_traffic(prompt_id: int, traffic: float, did: str | None = None) -> None:
    """Update the traffic allocation for a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        traffic: New traffic allocation (0.0 to 1.0)
        did: Decentralized Identifier for schema isolation
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    storage = await _get_storage(did=did)
    try:
        await storage.update_prompt_traffic(prompt_id, traffic)
    finally:
        await storage.disconnect()


async def update_prompt_status(prompt_id: int, status: str, did: str | None = None) -> None:
    """Update the status of a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (active, candidate, deprecated, rolled_back)
        did: Decentralized Identifier for schema isolation
    """
    storage = await _get_storage(did=did)
    try:
        await storage.update_prompt_status(prompt_id, status)
    finally:
        await storage.disconnect()


async def zero_out_all_except(prompt_ids: list[int], did: str | None = None) -> None:
    """Set traffic to 0 for all prompts except those in the given list.
    
    Args:
        prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
        did: Decentralized Identifier for schema isolation
    """
    storage = await _get_storage(did=did)
    try:
        await storage.zero_out_all_except(prompt_ids)
    finally:
        await storage.disconnect()