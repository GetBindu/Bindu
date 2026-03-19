"""Scheduler factory for creating scheduler backend instances.

This module provides a factory function to create schedulers based on
configuration settings. It supports easy switching between scheduler implementations
without changing application code.
"""

from __future__ import annotations as _annotations

from bindu.common.models import SchedulerConfig
from bindu.utils.logging import get_logger

from .base import Scheduler
from .memory_scheduler import InMemoryScheduler

# Import RedisScheduler conditionally
try:
    from .redis_scheduler import RedisScheduler

    REDIS_AVAILABLE = True
except ImportError:
    RedisScheduler = None  # type: ignore[assignment]  # redis not installed
    REDIS_AVAILABLE = False

logger = get_logger("bindu.server.scheduler.factory")

# Constants
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0


async def create_scheduler(config: SchedulerConfig | None = None) -> Scheduler:
    """Create scheduler backend based on configuration.

    Reads the scheduler type from config and creates the appropriate scheduler instance.
    If no config is provided, uses app_settings.scheduler defaults.
    """
    from bindu.settings import app_settings

    # Use settings if no config provided
    if config is None:
        scheduler_settings = app_settings.scheduler
        backend = scheduler_settings.backend
        logger.info(f"No scheduler config provided, using settings: {backend}")

        if backend == "memory":
            return InMemoryScheduler()
        elif backend == "redis":
            # Build config from settings
            config = SchedulerConfig(
                type="redis",
                redis_url=scheduler_settings.redis_url,
                redis_host=scheduler_settings.redis_host or DEFAULT_REDIS_HOST,
                redis_port=scheduler_settings.redis_port or DEFAULT_REDIS_PORT,
                redis_password=scheduler_settings.redis_password,
                redis_db=scheduler_settings.redis_db or DEFAULT_REDIS_DB,
                queue_name=scheduler_settings.queue_name,
                max_connections=scheduler_settings.max_connections,
                retry_on_timeout=scheduler_settings.retry_on_timeout,
                poll_timeout=scheduler_settings.poll_timeout,
            )
        else:
            raise ValueError(f"Unknown scheduler backend in settings: {backend}")

    backend = config.type.lower()

    logger.info(f"Creating scheduler backend: {backend}")

    if backend == "memory":
        logger.info("Using in-memory scheduler (single-process)")
        return InMemoryScheduler()

    elif backend == "redis":
        if not REDIS_AVAILABLE or RedisScheduler is None:
            raise ValueError(
                "Redis scheduler requires redis package. "
                "Install with: pip install redis[hiredis]"
            )

        logger.info("Using Redis scheduler (distributed, multi-process)")

        # Validate redis_url is provided
        redis_url = config.redis_url
        if not redis_url:
            # Try to construct URL from individual components if provided
            if (
                config.redis_host
                and config.redis_port is not None
                and config.redis_db is not None
            ):
                auth = f":{config.redis_password}@" if config.redis_password else ""
                redis_url = f"redis://{auth}{config.redis_host}:{config.redis_port}/{config.redis_db}"
            else:
                raise ValueError(
                    "Redis scheduler requires a Redis URL. "
                    "Please provide it via REDIS_URL environment variable or config."
                )

        scheduler = RedisScheduler(
            redis_url=redis_url,
            queue_name=config.queue_name,
            max_connections=config.max_connections,
            retry_on_timeout=config.retry_on_timeout,
            poll_timeout=config.poll_timeout,
        )

        return scheduler

    else:
        raise ValueError(
            f"Unknown scheduler backend: {backend}. Supported backends: memory, redis"
        )


async def close_scheduler(scheduler: Scheduler) -> None:
    """Close scheduler connection gracefully.

    Unconditionally calls __aexit__ as all Scheduler interfaces implement it.
    This prevents resource leaks (like unclosed anyio streams in InMemoryScheduler).
    """
    try:
        await scheduler.__aexit__(None, None, None)
        logger.info(f"{type(scheduler).__name__} connection closed")
    except Exception as e:
        logger.error(f"Error closing {type(scheduler).__name__}: {e}")
