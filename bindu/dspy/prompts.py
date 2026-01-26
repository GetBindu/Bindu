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

from bindu.server.storage.base import Storage
from bindu.server.storage.postgres_storage import PostgresStorage


async def _get_storage(storage: Storage | None = None, did: str | None = None) -> tuple[Storage, bool]:
    """Get a storage instance for prompt operations with DID isolation.
    
    Args:
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
    
    Returns:
        Tuple of (storage instance, should_disconnect) where should_disconnect indicates
        whether the caller is responsible for disconnecting
    """
    if storage is not None:
        # Use provided storage, caller manages lifecycle
        return storage, False
    
    # Create new storage, caller must disconnect
    new_storage = PostgresStorage(did=did)
    await new_storage.connect()
    return new_storage, True


async def get_active_prompt(storage: Storage | None = None, did: str | None = None) -> dict[str, Any] | None:
    """Get the current active prompt.
    
    Args:
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no active prompt exists
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        return await store.get_active_prompt()
    finally:
        if should_disconnect:
            await store.disconnect()


async def get_candidate_prompt(storage: Storage | None = None, did: str | None = None) -> dict[str, Any] | None:
    """Get the current candidate prompt.
    
    Args:
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no candidate prompt exists
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        return await store.get_candidate_prompt()
    finally:
        if should_disconnect:
            await store.disconnect()


async def insert_prompt(text: str, status: str, traffic: float, storage: Storage | None = None, did: str | None = None) -> int:
    """Insert a new prompt into the database.
    
    Args:
        text: The prompt text content
        status: The prompt status (active, candidate, deprecated, rolled_back)
        traffic: Traffic allocation (0.0 to 1.0)
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
        
    Returns:
        The ID of the newly inserted prompt
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        return await store.insert_prompt(text, status, traffic)
    finally:
        if should_disconnect:
            await store.disconnect()


async def update_prompt_traffic(prompt_id: int, traffic: float, storage: Storage | None = None, did: str | None = None) -> None:
    """Update the traffic allocation for a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        traffic: New traffic allocation (0.0 to 1.0)
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        await store.update_prompt_traffic(prompt_id, traffic)
    finally:
        if should_disconnect:
            await store.disconnect()


async def update_prompt_status(prompt_id: int, status: str, storage: Storage | None = None, did: str | None = None) -> None:
    """Update the status of a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (active, candidate, deprecated, rolled_back)
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        await store.update_prompt_status(prompt_id, status)
    finally:
        if should_disconnect:
            await store.disconnect()


async def zero_out_all_except(prompt_ids: list[int], storage: Storage | None = None, did: str | None = None) -> None:
    """Set traffic to 0 for all prompts except those in the given list.
    
    Args:
        prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
        storage: Optional existing storage instance to reuse
        did: Decentralized Identifier for schema isolation (only used if storage is None)
    """
    store, should_disconnect = await _get_storage(storage, did)
    try:
        await store.zero_out_all_except(prompt_ids)
    finally:
        if should_disconnect:
            await store.disconnect()