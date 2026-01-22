# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Prompt metrics tracking for canary deployment.

This module provides functionality to track and update prompt performance
metrics based on user feedback and interaction counts.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bindu.dspy.prompts import _get_database_url
from bindu.server.storage.schema import agent_prompts_table
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompt_metrics")


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
    if normalized_feedback_score is not None and not (
        0 <= normalized_feedback_score <= 1
    ):
        raise ValueError(
            f"normalized_feedback_score must be between 0 and 1, got {normalized_feedback_score}"
        )

    database_url = _get_database_url()

    engine = create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        echo=False,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            async with session.begin():
                # Fetch current prompt data
                stmt = select(agent_prompts_table).where(
                    agent_prompts_table.c.id == prompt_id
                )
                result = await session.execute(stmt)
                row = result.fetchone()

                if not row:
                    logger.warning(f"Prompt {prompt_id} not found, skipping metrics update")
                    return

                old_num_interactions = row.num_interactions or 0
                old_avg_feedback = row.average_feedback_score

                # Calculate new values
                new_num_interactions = old_num_interactions + 1

                if normalized_feedback_score is not None:
                    # Update average feedback score
                    if old_avg_feedback is None:
                        # First feedback
                        new_avg_feedback = normalized_feedback_score
                    else:
                        # Weighted average: ((old_avg * old_count) + new_feedback) / (old_count + 1)
                        new_avg_feedback = (
                            (float(old_avg_feedback) * old_num_interactions)
                            + normalized_feedback_score
                        ) / (old_num_interactions + 1)

                    logger.info(
                        f"Updating prompt {prompt_id}: num_interactions {old_num_interactions} -> {new_num_interactions}, "
                        f"avg_feedback {old_avg_feedback} -> {new_avg_feedback:.3f}"
                    )

                    # Update both metrics
                    stmt = (
                        update(agent_prompts_table)
                        .where(agent_prompts_table.c.id == prompt_id)
                        .values(
                            num_interactions=new_num_interactions,
                            average_feedback_score=new_avg_feedback,
                        )
                    )
                else:
                    # Only increment interactions
                    logger.info(
                        f"Updating prompt {prompt_id}: num_interactions {old_num_interactions} -> {new_num_interactions}"
                    )

                    stmt = (
                        update(agent_prompts_table)
                        .where(agent_prompts_table.c.id == prompt_id)
                        .values(num_interactions=new_num_interactions)
                    )

                await session.execute(stmt)

    finally:
        await engine.dispose()
