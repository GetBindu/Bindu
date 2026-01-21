# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy training guard to prevent conflicts during A/B testing.

This module provides safety checks to ensure DSPy training doesn't interfere
with active experiments.
"""

from __future__ import annotations

from bindu.utils.logging import get_logger

from .prompts import get_candidate_prompt

logger = get_logger("bindu.dspy.guard")


async def ensure_system_stable(agent_id: str | None = None) -> None:
    """Ensure system is stable before starting DSPy training.
    
    Checks if there's already an active candidate prompt being tested.
    If a candidate exists, it means an A/B test is in progress and we
    should not start new training until that experiment concludes.
    
    Args:
        agent_id: Agent identifier (currently unused, reserved for future
                 multi-agent support)
    
    Raises:
        RuntimeError: If a candidate prompt already exists (experiment active)
    """
    # Check if there's already a candidate prompt
    candidate = await get_candidate_prompt()
    
    if candidate is not None:
        logger.error(
            f"DSPy training blocked: candidate prompt (id={candidate['id']}) "
            "already exists. Experiment still active."
        )
        raise RuntimeError(
            "DSPy training blocked: experiment still active. "
            f"A candidate prompt (id={candidate['id']}) is currently being tested. "
            "Wait for the experiment to conclude before starting new training."
        )
    
    logger.info("System stable check passed: no active candidate prompt")
