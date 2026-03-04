# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose     |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Prompt router for canary deployment with weighted random selection.

This module provides functionality to route prompts from the database based
on traffic allocation percentages, enabling A/B testing and gradual rollouts.
"""

from __future__ import annotations

import random
from typing import Any

from bindu.dspy.prompt_storage import PromptStorage
from bindu.dspy.prompts import get_active_prompt, get_candidate_prompt
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompt_router")

_storage = PromptStorage()


async def route_prompt(
    initial_prompt: str | None = None,
    storage: PromptStorage = _storage,
) -> str:
    """Route to a prompt using weighted random selection based on traffic allocation.

    This function implements canary deployment by:
    1. Checking if storage is empty - if so, creates initial prompt
    2. Fetching active and candidate prompts from storage
    3. Using traffic percentages as weights for random selection
    4. Returning the selected prompt text

    Args:
        initial_prompt: Optional initial prompt text to create if storage is empty.
                       If storage is empty and this is None, returns the initial_prompt.
        storage: Optional existing storage instance to reuse

    Returns:
        The selected prompt text string. If storage is empty and no initial_prompt
        is provided, returns empty string.

    Example:
        >>> initial = "You are a helpful assistant"
        >>> prompt_text = await route_prompt(initial_prompt=initial)
        >>> agent.instructions = prompt_text
    """
    # Fetch both prompts from storage
    active = await get_active_prompt(storage=storage)
    candidate = await get_candidate_prompt(storage=storage)

    # If no prompts exist, create initial prompt if provided
    if not active and not candidate:
        if initial_prompt:
            logger.info("No prompts found in storage. Creating initial active prompt...")
            prompt_id = await storage.insert_prompt(
                text=initial_prompt,
                status="active",
                traffic=1.0
            )
            logger.info(f"Initial prompt created (id={prompt_id}) with 100% traffic")
            return initial_prompt
        
        logger.warning("No prompts found in storage and no initial_prompt provided")
        return initial_prompt or ""

    # If only active exists, use it
    if active and not candidate:
        logger.debug(
            f"Using active prompt {active['id']} (no candidate, traffic={active['traffic']:.2f})"
        )
        return active["prompt_text"]

    # If only candidate exists (shouldn't happen in normal flow), use it
    if candidate and not active:
        logger.warning(
            f"Only candidate prompt {candidate['id']} exists (no active), using candidate"
        )
        return candidate["prompt_text"]

    # Both exist - use weighted random selection
    active_traffic = float(active["traffic"])
    candidate_traffic = float(candidate["traffic"])

    # Normalize weights to ensure they sum to 1.0
    total_traffic = active_traffic + candidate_traffic
    if total_traffic == 0:
        # Both have 0 traffic - default to active
        logger.warning(
            "Both active and candidate have 0 traffic, defaulting to active"
        )
        return active["prompt_text"]

    # Weighted random choice
    choice = random.random()  # Returns float in [0.0, 1.0)
    
    if choice < active_traffic / total_traffic:
        selected = active
        logger.debug(
            f"Selected active prompt {active['id']} "
            f"(traffic={active_traffic:.2f}, roll={choice:.3f})"
        )
    else:
        selected = candidate
        logger.debug(
            f"Selected candidate prompt {candidate['id']} "
            f"(traffic={candidate_traffic:.2f}, roll={choice:.3f})"
        )

    return selected["prompt_text"]
