"""Storage factory for creating storage backend instances.

This module provides a factory function to create storage backends based on
configuration settings. It supports easy switching between storage implementations
without changing application code.

Usage:
    from bindu.server.storage.factory import create_storage

    # Create storage based on settings
    storage = await create_storage()

    # Use storage
    task = await storage.load_task(task_id)
"""

from __future__ import annotations as _annotations

import os

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import Storage
from .memory_storage import InMemoryStorage

# Import PostgresStorage conditionally
try:
    from .postgres_storage import PostgresStorage

    POSTGRES_AVAILABLE = True
except ImportError:
    PostgresStorage = None  # type: ignore[assignment]
    POSTGRES_AVAILABLE = False

logger = get_logger("bindu.server.storage.factory")


async def create_storage(did: str | None = None) -> Storage:
    """Create storage backend based on configuration."""

    backend = app_settings.storage.backend.lower()

    # Detect explicit environment variables
    storage_type_env = os.getenv("STORAGE_TYPE")
    database_url_env = os.getenv("DATABASE_URL")

    # Smart auto-detection (safe & test-friendly)
    if (
        storage_type_env is None
        and backend == "memory"
        and database_url_env is not None
        and POSTGRES_AVAILABLE
    ):
        logger.warning(
            "DATABASE_URL detected but STORAGE_TYPE not set. "
            "Auto-switching storage backend to 'postgres'. "
            "Set STORAGE_TYPE=memory to override."
        )
        backend = "postgres"

    logger.info(f"Creating storage backend: {backend}")

    # Memory backend
    if backend == "memory":
        logger.info("Using in-memory storage (non-persistent)")
        return InMemoryStorage()

    # PostgreSQL backend
    elif backend == "postgres":
        if not POSTGRES_AVAILABLE or PostgresStorage is None:
            raise ValueError(
                "PostgreSQL storage requires SQLAlchemy. "
                "Install with: pip install sqlalchemy[asyncio] asyncpg"
            )

        if not app_settings.storage.postgres_url:
            raise ValueError(
                "PostgreSQL storage requires a database URL. "
                "Please provide it via DATABASE_URL environment variable or config."
            )

        logger.info("Using PostgreSQL storage with SQLAlchemy (persistent)")

        storage = PostgresStorage(
            database_url=app_settings.storage.postgres_url,
            pool_min=app_settings.storage.postgres_pool_min,
            pool_max=app_settings.storage.postgres_pool_max,
            timeout=app_settings.storage.postgres_timeout,
            command_timeout=app_settings.storage.postgres_command_timeout,
            did=did,
        )

        await storage.connect()
        return storage

    else:
        raise ValueError(
            f"Unknown storage backend: {backend}. "
            "Supported backends: memory, postgres"
        )


async def close_storage(storage: Storage) -> None:
    """Close storage connection gracefully."""

    if (
        POSTGRES_AVAILABLE
        and PostgresStorage is not None
        and isinstance(storage, PostgresStorage)
    ):
        await storage.disconnect()
        logger.info("PostgreSQL storage connection closed")
    else:
        logger.debug(f"Storage {type(storage).__name__} does not require cleanup")