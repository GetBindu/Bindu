# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""PostgreSQL data access layer for DSPy prompts management.

This module provides database operations for managing agent prompts,
including CRUD operations and traffic distribution. It uses SQLAlchemy Core
with async operations for efficient database access.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bindu.server.storage.schema import agent_prompts_table
from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompts")


def _get_database_url() -> str:
    """Get and validate database URL from environment.
    
    Returns:
        Database URL configured for asyncpg
        
    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
    """
    database_url = os.getenv("STORAGE__POSTGRES_URL")
    if not database_url:
        raise RuntimeError("STORAGE__POSTGRES_URL environment variable not set")

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        database_url = f"postgresql+asyncpg://{database_url}"

    return database_url


async def _create_session() -> AsyncSession:
    """Create a database session.
    
    Returns:
        AsyncSession instance
    """
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

    return await session_factory().__aenter__()


async def get_active_prompt() -> dict[str, Any] | None:
    """Get the current active prompt.
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no active prompt exists
    """
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
            stmt = select(agent_prompts_table).where(
                agent_prompts_table.c.status == "active"
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            
            if row:
                return {
                    "id": row.id,
                    "prompt_text": row.prompt_text,
                    "status": row.status,
                    "traffic": float(row.traffic) if row.traffic is not None else 0.0,
                    "num_interactions": row.num_interactions if row.num_interactions is not None else 0,
                    "average_feedback_score": float(row.average_feedback_score) if row.average_feedback_score is not None else None,
                }
            
            return None
    finally:
        await engine.dispose()


async def get_candidate_prompt() -> dict[str, Any] | None:
    """Get the current candidate prompt.
    
    Returns:
        Dictionary containing prompt data (id, prompt_text, status, traffic)
        or None if no candidate prompt exists
    """
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
            stmt = select(agent_prompts_table).where(
                agent_prompts_table.c.status == "candidate"
            )
            result = await session.execute(stmt)
            row = result.fetchone()
            
            if row:
                return {
                    "id": row.id,
                    "prompt_text": row.prompt_text,
                    "status": row.status,
                    "traffic": float(row.traffic) if row.traffic is not None else 0.0,
                    "num_interactions": row.num_interactions if row.num_interactions is not None else 0,
                    "average_feedback_score": float(row.average_feedback_score) if row.average_feedback_score is not None else None,
                }
            
            return None
    finally:
        await engine.dispose()


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
    if not 0 <= traffic <= 1:
        raise ValueError(f"Traffic must be between 0 and 1, got {traffic}")
    
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
            stmt = agent_prompts_table.insert().values(
                prompt_text=text,
                status=status,
                traffic=traffic,
                num_interactions=0,
                average_feedback_score=None,
            ).returning(agent_prompts_table.c.id)
            
            result = await session.execute(stmt)
            await session.commit()
            
            prompt_id = result.scalar_one()
            logger.info(f"Inserted prompt {prompt_id} with status '{status}' and traffic {traffic}")
            return prompt_id
    finally:
        await engine.dispose()


async def update_prompt_traffic(prompt_id: int, traffic: float) -> None:
    """Update the traffic allocation for a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        traffic: New traffic allocation (0.0 to 1.0)
        
    Raises:
        ValueError: If traffic is not in range [0, 1]
    """
    if not 0 <= traffic <= 1:
        raise ValueError(f"Traffic must be between 0 and 1, got {traffic}")
    
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
            stmt = (
                update(agent_prompts_table)
                .where(agent_prompts_table.c.id == prompt_id)
                .values(traffic=traffic)
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"Updated traffic for prompt {prompt_id} to {traffic}")
    finally:
        await engine.dispose()


async def update_prompt_status(prompt_id: int, status: str) -> None:
    """Update the status of a specific prompt.
    
    Args:
        prompt_id: The ID of the prompt to update
        status: New status (active, candidate, deprecated, rolled_back)
    """
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
            stmt = (
                update(agent_prompts_table)
                .where(agent_prompts_table.c.id == prompt_id)
                .values(status=status)
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"Updated status for prompt {prompt_id} to '{status}'")
    finally:
        await engine.dispose()


async def zero_out_all_except(prompt_ids: list[int]) -> None:
    """Set traffic to 0 for all prompts except those in the given list.
    
    Args:
        prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
    """
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
            stmt = (
                update(agent_prompts_table)
                .where(agent_prompts_table.c.id.notin_(prompt_ids))
                .values(traffic=0)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            logger.info(
                f"Zeroed out traffic for {result.rowcount} prompts "
                f"(preserving IDs: {prompt_ids})"
            )
    finally:
        await engine.dispose()
