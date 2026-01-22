# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Prompt selector for canary deployment with weighted random selection.

This module provides functionality to select prompts from the database based
on traffic allocation percentages, enabling A/B testing and gradual rollouts.
"""

from __future__ import annotations

import random
from typing import Any

from bindu.dspy.prompts import get_active_prompt, get_candidate_prompt
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompt_selector")


async def select_prompt_with_canary() -> dict[str, Any] | None:
    """Select a prompt using weighted random selection based on traffic allocation.

    This function implements canary deployment by:
    1. Fetching active and candidate prompts from database
    2. Using traffic percentages as weights for random selection
    3. Returning the selected prompt with its metadata

    Returns:
        Selected prompt dict with keys: id, prompt_text, status, traffic,
        num_interactions, average_feedback_score
        Returns None if no prompts are available

    Example:
        >>> prompt = await select_prompt_with_canary()
        >>> if prompt:
        ...     system_message = prompt["prompt_text"]
        ...     logger.info(f"Using prompt {prompt['id']} with status {prompt['status']}")
    """
    # Fetch both prompts from database
    active = await get_active_prompt()
    candidate = await get_candidate_prompt()

    # If no prompts exist, return None
    if not active and not candidate:
        logger.warning("No prompts found in database (no active or candidate)")
        return None

    # If only active exists, use it
    if active and not candidate:
        logger.debug(
            f"Using active prompt {active['id']} (no candidate, traffic={active['traffic']:.2f})"
        )
        return active

    # If only candidate exists (shouldn't happen in normal flow), use it
    if candidate and not active:
        logger.warning(
            f"Only candidate prompt {candidate['id']} exists (no active), using candidate"
        )
        return candidate

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
        return active

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

    return selected
