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
from bindu.server.storage.base import Storage
from bindu.server.storage.postgres_storage import PostgresStorage
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


async def promote_step(active: dict, candidate: dict, storage: Storage, did: str | None = None) -> None:
    """Promote candidate by increasing its traffic by 0.1 and decreasing active's.

    Args:
        active: Active prompt data with id and current traffic
        candidate: Candidate prompt data with id and current traffic
        storage: Storage instance to use for database operations
        did: Decentralized Identifier for schema isolation
    """
    traffic_step = app_settings.dspy.canary_traffic_step
    new_candidate_traffic = min(1.0, candidate["traffic"] + traffic_step)
    new_active_traffic = max(0.0, active["traffic"] - traffic_step)

    logger.info(
        f"Promoting candidate: traffic {candidate['traffic']:.1f} -> "
        f"{new_candidate_traffic:.1f}, active {active['traffic']:.1f} -> "
        f"{new_active_traffic:.1f}"
    )

    await update_prompt_traffic(candidate["id"], new_candidate_traffic, storage=storage, did=did)
    await update_prompt_traffic(active["id"], new_active_traffic, storage=storage, did=did)

    # Check for stabilization
    await _check_stabilization(active, candidate, new_active_traffic, new_candidate_traffic, storage=storage, did=did)


async def rollback_step(active: dict, candidate: dict, storage: Storage, did: str | None = None) -> None:
    """Rollback candidate by decreasing its traffic by 0.1 and increasing active's.

    Args:
        active: Active prompt data with id and current traffic
        candidate: Candidate prompt data with id and current traffic
        storage: Storage instance to use for database operations
        did: Decentralized Identifier for schema isolation
    """
    traffic_step = app_settings.dspy.canary_traffic_step
    new_candidate_traffic = max(0.0, candidate["traffic"] - traffic_step)
    new_active_traffic = min(1.0, active["traffic"] + traffic_step)

    logger.info(
        f"Rolling back candidate: traffic {candidate['traffic']:.1f} -> "
        f"{new_candidate_traffic:.1f}, active {active['traffic']:.1f} -> "
        f"{new_active_traffic:.1f}"
    )

    await update_prompt_traffic(candidate["id"], new_candidate_traffic, storage=storage, did=did)
    await update_prompt_traffic(active["id"], new_active_traffic, storage=storage, did=did)

    # Check for stabilization
    await _check_stabilization(active, candidate, new_active_traffic, new_candidate_traffic, storage=storage, did=did)


async def _check_stabilization(
    active: dict, candidate: dict, active_traffic: float, candidate_traffic: float, storage: Storage, did: str | None = None
) -> None:
    """Check if the system has stabilized and update statuses accordingly.

    Args:
        active: Active prompt data
        candidate: Candidate prompt data
        active_traffic: New active traffic value
        candidate_traffic: New candidate traffic value
        storage: Storage instance to use for database operations
        did: Decentralized Identifier for schema isolation
    """
    # Stabilization: one prompt at 1.0, the other at 0.0
    if active_traffic == 1.0 and candidate_traffic == 0.0:
        # Active won, candidate is rolled back
        logger.info(
            f"System stabilized: active won, setting candidate {candidate['id']} "
            f"to rolled_back"
        )
        await update_prompt_status(candidate["id"], "rolled_back", storage=storage, did=did)

    elif candidate_traffic == 1.0 and active_traffic == 0.0:
        # Candidate won, promote to active and deprecate old active
        logger.info(
            f"System stabilized: candidate won, promoting candidate {candidate['id']} "
            f"to active and deprecating old active {active['id']}"
        )
        await update_prompt_status(candidate["id"], "active", storage=storage, did=did)
        await update_prompt_status(active["id"], "deprecated", storage=storage, did=did)


async def run_canary_controller(did: str | None = None) -> None:
    """Main canary controller logic.

    Compares active and candidate prompts and adjusts traffic based on metrics.
    If no candidate exists, the system is considered stable.
    
    Args:
        did: Decentralized Identifier for schema isolation (required for multi-tenancy)
    """
    logger.info(f"Starting canary controller (DID: {did or 'public'})")
    
    # Create a single storage instance for the entire canary controller run
    # This is more efficient than creating/destroying connections for each operation
    storage = PostgresStorage(did=did)
    await storage.connect()
    
    try:
        active = await get_active_prompt(storage=storage, did=did)
        candidate = await get_candidate_prompt(storage=storage, did=did)

        if not candidate:
            logger.info("No candidate prompt - system stable")
            return

        if not active:
            logger.warning("No active prompt found - cannot run canary controller")
            return

        # Compare metrics to determine winner
        winner = compare_metrics(active, candidate)

        if winner == "candidate":
            await promote_step(active, candidate, storage=storage, did=did)
        elif winner == "active":
            await rollback_step(active, candidate, storage=storage, did=did)
        else:
            logger.info("No clear winner - maintaining current traffic distribution")
    
    finally:
        # Always disconnect storage, even if an error occurred
        await storage.disconnect()
        logger.info("Canary controller storage connection closed")