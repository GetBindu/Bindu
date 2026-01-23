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

# Singleton storage instance for prompt operations
_storage: PostgresStorage | None = None


async def _get_storage() -> PostgresStorage:
    """Get or create the storage instance for prompt operations.
    
    Returns:
        Initialized PostgresStorage instance
    """
    global _storage
    
    if _storage is None:
        _storage = PostgresStorage()
        await _storage.connect()
    
    return _storage


async def get_active_prompt() -> dict[str, Any] | None:
    """Get the current active prompt.
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no active prompt exists
    """
    storage = await _get_storage()
    return await storage.get_active_prompt()


async def get_candidate_prompt() -> dict[str, Any] | None:
    """Get the current candidate prompt.
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no candidate prompt exists
    """
    storage = await _get_storage()
    return await storage.get_candidate_prompt()


async def insert_prompt(text: str, status: str, traffic: float) -> int:
    """Insert a new prompt into the database.
    
    Args:
        text: The prompt text content
        status: The prompt status (active, candidate, deprecated, rolled_back)
        traffic: Traffic allocation (0.0 to 1.0)
        
    Returns:
        The ID of the newly inserted prompt
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    storage = await _get_storage()
    return await storage.insert_prompt(text, status, traffic)


async def update_prompt_traffic(prompt_id: int, traffic: float) -> None:
    """Update the traffic allocation for a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        traffic: New traffic allocation (0.0 to 1.0)
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    storage = await _get_storage()
    await storage.update_prompt_traffic(prompt_id, traffic)


async def update_prompt_status(prompt_id: int, status: str) -> None:
    """Update the status of a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (active, candidate, deprecated, rolled_back)
    """
    storage = await _get_storage()
    await storage.update_prompt_status(prompt_id, status)


async def zero_out_all_except(prompt_ids: list[int]) -> None:
    """Set traffic to 0 for all prompts except those in the given list.
    
    Args:
        prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
    """
    storage = await _get_storage()
    await storage.zero_out_all_except(prompt_ids)


async def update_prompt_metrics(
    prompt_id: int, normalized_feedback_score: float | None = None
) -> None:
    """Update prompt metrics: increment interactions and update average feedback.

    Args:
        prompt_id: ID of the prompt to update
        normalized_feedback_score: Optional feedback score between 0 and 1.
            If provided, updates average_feedback_score.
            If None, only increments num_interactions.

    The average feedback is calculated using the formula:
        new_avg = ((old_avg * old_count) + new_feedback) / (old_count + 1)

    Raises:
        ValueError: If normalized_feedback_score is not in range [0, 1]
    """
    storage = await _get_storage()
    await storage.update_prompt_metrics(prompt_id, normalized_feedback_score)