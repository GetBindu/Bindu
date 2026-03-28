"""Factory for creating voice session manager backends.

This module provides a factory function to create session managers based on
configuration settings. It supports easy switching between session
storage backends without changing application code.
"""

from __future__ import annotations as _annotations

from typing import TYPE_CHECKING

from bindu.extensions.voice.session_manager import VoiceSessionManager
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.settings import VoiceSettings

logger = get_logger("bindu.voice.session_factory")

# Import RedisSessionManager conditionally
try:
    from .redis_session_manager import RedisVoiceSessionManager

    REDIS_AVAILABLE = True
except ImportError:
    RedisVoiceSessionManager = None  # type: ignore[assignment]  # redis not installed
    REDIS_AVAILABLE = False


async def create_session_manager(
    settings: VoiceSettings | None = None,
) -> VoiceSessionManager:
    """Create session manager backend based on configuration.

    Args:
        settings: Voice settings. If not provided, uses app_settings.voice.

    Returns:
        VoiceSessionManager: An instance of the appropriate session manager.

    Raises:
        ValueError: If Redis backend is requested but Redis is not available.
    """
    from bindu.settings import app_settings

    voice_settings = settings or app_settings.voice
    backend = voice_settings.session_backend

    logger.info(f"Creating voice session manager with backend: {backend}")

    if backend == "memory":
        logger.info("Using in-memory session manager (single-process)")
        return VoiceSessionManager(
            max_sessions=voice_settings.max_concurrent_sessions,
            session_timeout=voice_settings.session_timeout,
        )

    elif backend == "redis":
        if not REDIS_AVAILABLE or RedisVoiceSessionManager is None:
            raise ValueError(
                "Redis session manager requires redis package. "
                "Install with: pip install redis[hiredis]"
            )

        logger.info("Using Redis session manager (distributed, multi-process)")

        redis_url = voice_settings.redis_url
        if not redis_url:
            raise ValueError(
                "Redis session manager requires a Redis URL. "
                "Please provide it via VOICE__REDIS_URL environment variable or config."
            )

        manager = RedisVoiceSessionManager(
            redis_url=redis_url,
            max_sessions=voice_settings.max_concurrent_sessions,
            session_timeout=voice_settings.session_timeout,
            redis_session_ttl=voice_settings.redis_session_ttl,
        )

        # Enter async context to initialize Redis connection
        await manager.__aenter__()
        return manager

    else:
        raise ValueError(
            f"Unknown session backend: {backend}. Supported backends: memory, redis"
        )


async def close_session_manager(manager: VoiceSessionManager) -> None:
    """Close session manager connection gracefully.

    Args:
        manager: The session manager to close.
    """
    try:
        # Check if it's a Redis-backed manager with __aexit__ method
        if hasattr(manager, "__aexit__"):
            await manager.__aexit__(None, None, None)
            logger.info(f"{type(manager).__name__} connection closed")
        else:
            # For in-memory manager, just stop cleanup loop
            if hasattr(manager, "stop_cleanup_loop"):
                await manager.stop_cleanup_loop()
                logger.info(f"{type(manager).__name__} cleanup loop stopped")
    except Exception as e:
        logger.error(f"Error closing {type(manager).__name__}: {e}")