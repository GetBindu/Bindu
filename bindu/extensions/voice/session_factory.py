"""Factory for creating voice session manager backends.

This module provides a factory function to create session managers based on
configuration settings. It supports easy switching between session
storage backends without changing application code.
"""

from __future__ import annotations as _annotations

from typing import TYPE_CHECKING, Literal, Protocol

from bindu.extensions.voice.session_manager import VoiceSessionManager
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.extensions.voice.session_manager import VoiceSession
    from bindu.settings import VoiceSettings

logger = get_logger("bindu.voice.session_factory")

# Import RedisSessionManager conditionally
try:
    from .redis_session_manager import RedisVoiceSessionManager

    REDIS_AVAILABLE = True
except ImportError:
    RedisVoiceSessionManager = None  # type: ignore[assignment]  # redis not installed
    REDIS_AVAILABLE = False


class SessionManagerBackend(Protocol):
    """Common interface supported by voice session manager backends."""

    async def create_session(
        self,
        context_id: str,
        *,
        session_token: str | None = None,
        session_token_expires_at: float | None = None,
    ) -> VoiceSession:
        """Create a voice session for a context ID."""

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Get an existing session by ID."""

    async def end_session(self, session_id: str) -> None:
        """End and cleanup a voice session."""

    async def update_state(
        self,
        session_id: str,
        state: Literal["connecting", "active", "ending", "ended"],
    ) -> None:
        """Update the lifecycle state of a session."""

    async def get_active_count(self) -> int:
        """Return the number of sessions that are not ended."""

    async def start_cleanup_loop(self) -> None:
        """Start periodic cleanup for stale sessions."""

    async def stop_cleanup_loop(self) -> None:
        """Stop the background cleanup task."""


async def create_session_manager(
    settings: VoiceSettings | None = None,
) -> SessionManagerBackend:
    """Create session manager backend based on configuration.

    Args:
        settings: Voice settings. If not provided, uses app_settings.voice.

    Returns:
        SessionManagerBackend: An instance of the appropriate session manager backend.

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

    if backend == "redis":
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
        try:
            await manager.__aenter__()
        except Exception:
            # Ensure cleanup on initialization failure
            await manager.__aexit__(None, None, None)
            raise
        return manager

    raise ValueError(
        f"Unknown session backend: {backend}. Supported backends: memory, redis"
    )


async def close_session_manager(manager: SessionManagerBackend) -> None:
    """Close session manager connection gracefully.

    Args:
        manager: The session manager to close.
    """
    cleanup_error: Exception | None = None
    try:
        await manager.stop_cleanup_loop()
        logger.info(f"{type(manager).__name__} cleanup loop stopped")
    except Exception as e:
        cleanup_error = e
        logger.error(f"Error stopping cleanup loop for {type(manager).__name__}: {e}")
    finally:
        if (
            REDIS_AVAILABLE
            and RedisVoiceSessionManager is not None
            and isinstance(manager, RedisVoiceSessionManager)
        ):
            try:
                await manager.__aexit__(None, None, None)
                logger.info(f"{type(manager).__name__} connection closed")
            except Exception as e:
                if cleanup_error is not None:
                    e.__cause__ = cleanup_error
                cleanup_error = e
                logger.error(f"Error closing {type(manager).__name__}: {e}")

    if cleanup_error is not None:
        raise cleanup_error
