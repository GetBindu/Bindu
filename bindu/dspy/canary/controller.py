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

from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB

from bindu.settings import app_settings
from bindu.server.storage.postgres_storage import PostgresStorage
from bindu.server.storage.schema import task_feedback_table, tasks_table
from bindu.dspy.prompts import (
    get_active_prompt,
    get_candidate_prompt,
    update_prompt_status,
    update_prompt_traffic,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.canary.controller")


async def fetch_tasks_with_feedback_by_prompt_id(
    storage: PostgresStorage,
    prompt_id: str,
) -> list[dict[str, Any]]:
    """Fetch tasks with their feedback for a given prompt ID.

    Args:
        storage: PostgresStorage instance (must already be connected)
        prompt_id: The prompt ID to filter tasks by

    Returns:
        List of dicts with keys: task_id, history, created_at, feedback_data
    """
    storage._ensure_connected()

    async def _fetch():
        async with storage._get_session_with_schema() as session:
            # LEFT JOIN tasks with feedback to get all tasks and their feedback (if any)
            stmt = (
                select(
                    tasks_table.c.id.label("task_id"),
                    tasks_table.c.history,
                    tasks_table.c.created_at,
                    task_feedback_table.c.feedback_data,
                )
                .select_from(tasks_table)
                .outerjoin(
                    task_feedback_table,
                    tasks_table.c.id == task_feedback_table.c.task_id,
                )
                .where(tasks_table.c.prompt_id == prompt_id)
                .order_by(tasks_table.c.created_at.desc())
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            return [
                {
                    "task_id": row.task_id,
                    "history": row.history,
                    "created_at": row.created_at,
                    "feedback_data": row.feedback_data,
                }
                for row in rows
            ]

    return await storage._retry_on_connection_error(_fetch)


def normalize_feedback_score(feedback_data: dict[str, Any] | None) -> float | None:
    """Normalize feedback data to a numeric score [0.0, 1.0].

    Accepts multiple feedback formats:
    - { rating: 1-5 } → normalized to 0.0-1.0
    - { thumbs_up: true/false } → 1.0 or 0.0
    - Missing/invalid → None

    Args:
        feedback_data: Raw feedback data from database

    Returns:
        Normalized score between 0.0 and 1.0, or None if no valid feedback
    """
    if not feedback_data:
        return None

    # Try rating format (1-5 scale)
    rating = feedback_data.get("rating")
    if rating is not None:
        try:
            rating_val = float(rating)
            if 1 <= rating_val <= 5:
                return rating_val / 5.0
        except (ValueError, TypeError):
            pass

    # Try thumbs_up format
    thumbs_up = feedback_data.get("thumbs_up")
    if thumbs_up is not None:
        if isinstance(thumbs_up, bool):
            return 1.0 if thumbs_up else 0.0
        # Handle string "true"/"false"
        if isinstance(thumbs_up, str):
            thumbs_up_lower = thumbs_up.lower()
            if thumbs_up_lower in ("true", "1", "yes"):
                return 1.0
            elif thumbs_up_lower in ("false", "0", "no"):
                return 0.0

    return None


async def calculate_prompt_metrics(
    storage: PostgresStorage,
    prompt_id: str,
) -> dict[str, Any]:
    """Calculate metrics for a prompt by fetching all its tasks and feedback.

    Args:
        storage: PostgresStorage instance (must already be connected)
        prompt_id: The prompt ID to calculate metrics for

    Returns:
        Dict with keys:
        - num_interactions: Total number of tasks for this prompt
        - average_feedback_score: Average of all normalized feedback scores (or None)
    """
    tasks = await fetch_tasks_with_feedback_by_prompt_id(storage, prompt_id)

    num_interactions = len(tasks)
    feedback_scores = []

    for task in tasks:
        score = normalize_feedback_score(task["feedback_data"])
        if score is not None:
            feedback_scores.append(score)

    average_feedback_score = (
        sum(feedback_scores) / len(feedback_scores) if feedback_scores else None
    )

    logger.info(
        f"Calculated metrics for prompt {prompt_id}: "
        f"num_interactions={num_interactions}, "
        f"average_feedback_score={average_feedback_score}"
    )

    return {
        "num_interactions": num_interactions,
        "average_feedback_score": average_feedback_score,
    }


async def compare_metrics(
    storage: PostgresStorage,
    active_prompt_id: str,
    candidate_prompt_id: str,
) -> Literal["active", "candidate", None]:
    """Compare metrics between active and candidate prompts.

    Fetches tasks and feedback from the database for both prompts and
    calculates metrics on the spot.

    Args:
        storage: PostgresStorage instance (must already be connected)
        active_prompt_id: ID of the active prompt
        candidate_prompt_id: ID of the candidate prompt

    Returns:
        "active" if active is better, "candidate" if candidate is better, None for tie
        Returns None if candidate doesn't have enough interactions yet
    """
    # Calculate metrics for both prompts from database
    active_metrics = await calculate_prompt_metrics(storage, active_prompt_id)
    candidate_metrics = await calculate_prompt_metrics(storage, candidate_prompt_id)

    # Check if candidate has enough interactions
    candidate_interactions = candidate_metrics["num_interactions"]
    min_threshold = app_settings.dspy.min_canary_interactions_threshold
    if candidate_interactions < min_threshold:
        logger.info(
            f"Candidate has {candidate_interactions} interactions, "
            f"needs {min_threshold} - treating as tie"
        )
        return None

    active_score = active_metrics["average_feedback_score"]
    candidate_score = candidate_metrics["average_feedback_score"]

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
    if new_candidate_traffic >= 0.95 and new_active_traffic <= 0.05:
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


async def run_canary_controller(did: str | None = None) -> None:
    """Main canary controller logic.

    Compares active and candidate prompts and adjusts traffic based on metrics.
    If no candidate exists, the system is considered stable.

    Args:
        did: Decentralized Identifier for schema isolation (required for multi-tenancy)
    """
    logger.info(f"Starting canary controller (DID: {did or 'public'})")

    # Create storage instance with DID for schema isolation
    storage = PostgresStorage(did=did)

    try:
        # Connect to database
        await storage.connect()

        # Get active and candidate prompts from prompt storage
        active = await get_active_prompt()
        candidate = await get_candidate_prompt()

        if not candidate:
            logger.info("No candidate prompt - system stable")
            return

        if not active:
            logger.warning("No active prompt found - cannot run canary controller")
            return

        # Compare metrics by fetching from database
        winner = await compare_metrics(
            storage,
            active_prompt_id=active["id"],
            candidate_prompt_id=candidate["id"],
        )

        if winner == "candidate":
            await promote_step(active, candidate)
        elif winner == "active":
            await hard_rollback(active, candidate)
        else:
            logger.info("No clear winner - maintaining current traffic distribution")
    except Exception as e:
        logger.error(f"Error in canary controller: {e}", exc_info=True)
    finally:
        # Always clean up the database connection
        await storage.disconnect()