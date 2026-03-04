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
from bindu.dspy.context import set_prompt_id
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompt_router")

storage = PromptStorage()

async def route_prompt(
    initial_prompt: str | None = None
) -> str:
    """Route to a prompt using weighted random selection based on traffic allocation.

    This function implements canary deployment by:
    1. Checking if storage is empty - if so, creates initial prompt
    2. Fetching active and candidate prompts from storage
    3. Using traffic percentages as weights for random selection
    4. Returning the selected prompt text
    5. Storing the prompt_id in async context for worker to retrieve

    Args:
        initial_prompt: Optional initial prompt text to create if storage is empty.
                       If storage is empty and this is None, returns the initial_prompt.

    Returns:
        The selected prompt text string. The prompt_id is stored in async context
        via set_prompt_id() for the worker to retrieve.

    Example:
        >>> initial = "You are a helpful assistant"
        >>> prompt_text = await route_prompt(initial_prompt=initial)
        >>> agent.instructions = prompt_text
        >>> return agent.run(input=messages)  # Worker reads prompt_id from context
    """
    # Fetch both prompts from storage
    active = await get_active_prompt()
    candidate = await get_candidate_prompt()

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
            set_prompt_id(prompt_id)  # Store in context for worker
            return initial_prompt
        
        logger.warning("No prompts found in storage and no initial_prompt provided")
        set_prompt_id(None)  # Clear context
        return initial_prompt or ""

    # If only active exists, use it
    if active and not candidate:
        logger.debug(
            f"Using active prompt {active['id']} (no candidate, traffic={active['traffic']:.2f})"
        )
        set_prompt_id(active["id"])  # Store in context for worker
        return active["prompt_text"]

    # If only candidate exists (shouldn't happen in normal flow), use it
    if candidate and not active:
        logger.warning(
            f"Only candidate prompt {candidate['id']} exists (no active), using candidate"
        )
        set_prompt_id(candidate["id"])  # Store in context for worker
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
        set_prompt_id(active["id"])  # Store in context for worker
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

    set_prompt_id(selected["id"])  # Store in context for worker
    return selected["prompt_text"]
