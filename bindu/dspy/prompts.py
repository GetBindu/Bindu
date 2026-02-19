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
using a JSON file storage for persistence.
"""

from __future__ import annotations

from collections import UserString
from typing import Any

from bindu.dspy.prompt_storage import PromptStorage
from bindu.server.storage.base import Storage

# Initialize global prompt storage
_storage = PromptStorage()


class Prompt(UserString):
    """A prompt class that automatically saves itself to storage.
    
    This class behaves like a string for compatibility with agent frameworks
    (like Agno) that expect string instructions, but handles persistence
    behind the scenes.
    """
    
    def __init__(self, text: str, status: str = "active", traffic: float = 1.0):
        """Initialize and save the prompt.

        Args:
            text: The prompt text
            status: Initial status (active, candidate, etc.)
            traffic: Traffic allocation (0.0 to 1.0)
        """
        super().__init__(text)
        self.status = status
        self.traffic = traffic
        # Synchronously save to storage
        self.id = _storage.insert_prompt_sync(text, status, traffic)

    def __str__(self) -> str:
        """Return the prompt text."""
        return self.data


async def get_active_prompt(storage: Storage | None = None, did: str | None = None) -> dict[str, Any] | None:
    """Get the current active prompt.
    
    Args:
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no active prompt exists
    """
    return await _storage.get_active_prompt()


async def get_candidate_prompt(storage: Storage | None = None, did: str | None = None) -> dict[str, Any] | None:
    """Get the current candidate prompt.
    
    Args:
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no candidate prompt exists
    """
    return await _storage.get_candidate_prompt()


async def insert_prompt(text: str, status: str, traffic: float, storage: Storage | None = None, did: str | None = None) -> str:
    """Insert a new prompt into the storage.
    
    Args:
        text: The prompt text content
        status: The prompt status (active, candidate, deprecated, rolled_back)
        traffic: Traffic allocation (0.0 to 1.0)
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
        
    Returns:
        The ID of the newly inserted prompt (UUID string)
    """
    return await _storage.insert_prompt(text, status, traffic)


async def update_prompt_traffic(prompt_id: str, traffic: float, storage: Storage | None = None, did: str | None = None) -> None:
    """Update the traffic allocation for a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        traffic: New traffic allocation (0.0 to 1.0)
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
    """
    await _storage.update_prompt_traffic(prompt_id, traffic)


async def update_prompt_status(prompt_id: str, status: str, storage: Storage | None = None, did: str | None = None) -> None:
    """Update the status of a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (active, candidate, deprecated, rolled_back)
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
    """
    await _storage.update_prompt_status(prompt_id, status)


async def zero_out_all_except(prompt_ids: list[str], storage: Storage | None = None, did: str | None = None) -> None:
    """Set traffic to 0 for all prompts except those in the given list.
    
    Args:
        prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
        storage: Ignored (kept for compatibility)
        did: Ignored (kept for compatibility)
    """
    await _storage.zero_out_all_except(prompt_ids)
