# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Canary controller for gradual prompt rollout based on feedback metrics.

This module manages A/B testing between active and candidate prompts by
gradually shifting traffic based on average feedback scores. It implements
a canary deployment strategy to safely roll out new prompts.
"""

from __future__ import annotations

from typing import Literal

from bindu.settings import app_settings
from bindu.dspy.prompts import (
    get_active_prompt,
    get_candidate_prompt,
    update_prompt_status,
    update_prompt_traffic,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.canary.controller")

def compare_metrics(
    active: dict, candidate: dict
) -> Literal["active", "candidate", None]:
    """Compare metrics between active and candidate prompts.

    Args:
        active: Active prompt data with num_interactions and average_feedback_score
        candidate: Candidate prompt data with num_interactions and average_feedback_score

    Returns:
        "active" if active is better, "candidate" if candidate is better, None for tie
        Returns None if candidate doesn't have enough interactions yet
    """
    # Check if candidate has enough interactions
    candidate_interactions = candidate.get("num_interactions", 0)
    min_threshold = app_settings.dspy.min_canary_interactions_threshold
    if candidate_interactions < min_threshold:
        logger.info(
            f"Candidate has {candidate_interactions} interactions, "
            f"needs {min_threshold} - treating as tie"
        )
        return None

    active_score = active.get("average_feedback_score")
    candidate_score = candidate.get("average_feedback_score")

    # If either doesn't have feedback yet, treat as tie
    if active_score is None or candidate_score is None:
        logger.info(
            f"Missing feedback scores (active={active_score}, "
            f"candidate={candidate_score}) - treating as tie"
        )
        return None

    # Compare scores
    if candidate_score > active_score:
        logger.info(
            f"Candidate is winning (score={candidate_score:.3f} vs "
            f"active={active_score:.3f})"
        )
        return "candidate"
    elif active_score > candidate_score:
        logger.info(
            f"Active is winning (score={active_score:.3f} vs "
            f"candidate={candidate_score:.3f})"
        )
        return "active"
    else:
        logger.info(
            f"Scores are tied (both={active_score:.3f}) - treating as tie"
        )
        return None


async def promote_step(active: dict, candidate: dict) -> None:
    """Promote candidate by increasing its traffic by 0.1 and decreasing active's.

    Args:
        active: Active prompt data with id and current traffic
        candidate: Candidate prompt data with id and current traffic
        storage: Storage instance to use for database operations
    """
    traffic_step = app_settings.dspy.canary_traffic_step
    new_candidate_traffic = min(1.0, candidate["traffic"] + traffic_step)
    new_active_traffic = max(0.0, active["traffic"] - traffic_step)

    logger.info(
        f"Promoting candidate: traffic {candidate['traffic']:.1f} -> "
        f"{new_candidate_traffic:.1f}, active {active['traffic']:.1f} -> "
        f"{new_active_traffic:.1f}"
    )

    await update_prompt_traffic(candidate["id"], new_candidate_traffic)
    await update_prompt_traffic(active["id"], new_active_traffic)

    # Check for stabilization
    if new_candidate_traffic == 1.0 and new_active_traffic == 0.0:
        logger.info(
            f"System stabilized: candidate won, promoting candidate {candidate['id']} "
            f"to active and deprecating old active {active['id']}"
        )
        await update_prompt_status(candidate["id"], "active")
        await update_prompt_status(active["id"], "deprecated")

async def hard_rollback(active: dict, candidate: dict) -> None:
    """Immediately roll back candidate by setting its traffic to 0 and
    restoring active to 1.0.

    Args:
        active: Active prompt data with id and current traffic
        candidate: Candidate prompt data with id and current traffic
        storage: Storage instance to use for database operations
    """
    logger.warning(
        f"Hard rollback triggered: candidate {candidate['id']} "
        f"loses to active {active['id']}. "
        f"Setting candidate traffic to 0 and active to 1.0."
    )

    # Immediately restore traffic split
    await update_prompt_traffic(candidate["id"], 0.0)
    await update_prompt_traffic(active["id"], 1.0)

    # Mark candidate as rolled back
    await update_prompt_status(
        candidate["id"], "rolled_back"
    )


async def run_canary_controller() -> None:
    """Main canary controller logic.

    Compares active and candidate prompts and adjusts traffic based on metrics.
    If no candidate exists, the system is considered stable.
    
    Args:
        storage: PromptStorage instance to use for database operations
    """
    logger.info(f"Starting canary controller")
    
    try:
        active = await get_active_prompt()
        candidate = await get_candidate_prompt()

        if not candidate:
            logger.info("No candidate prompt - system stable")
            return

        if not active:
            logger.warning("No active prompt found - cannot run canary controller")
            return

        # Compare metrics to determine winner
        winner = compare_metrics(active, candidate)

        if winner == "candidate":
            await promote_step(active, candidate)
        elif winner == "active":
            await hard_rollback(active, candidate)
        else:
            logger.info("No clear winner - maintaining current traffic distribution")
    except Exception as e:
        logger.error(f"Error in canary controller: {e}", exc_info=True)