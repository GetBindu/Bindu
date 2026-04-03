"""Redis-backed voice session manager.

Provides multi-worker compatible session storage using Redis as the backend,
enabling session lookup across Uvicorn workers.
"""

from __future__ import annotations

import asyncio
import json
from typing import Literal, Any

import redis.asyncio as redis
from uuid import uuid4

from bindu.extensions.voice.session_manager import VoiceSession
from bindu.utils.logging import get_logger

logger = get_logger("bindu.voice.redis_session_manager")

# Constants
REDIS_KEY_PREFIX = "voice:sessions"
DEFAULT_SESSION_TTL = 300  # seconds


_CREATE_SESSION_LUA = """
-- Atomically creates a session if the number of active sessions is below the limit.
--
-- KEYS[1]: The key for the new session to create.
-- ARGV[1]: The pattern for scanning session keys (e.g., 'voice:sessions:*').
-- ARGV[2]: The maximum number of sessions allowed.
-- ARGV[3]: The serialized session data to store.
-- ARGV[4]: The TTL for the new session key.
--
-- Returns: 1 if the session was created, 0 otherwise.
local keys = redis.call('keys', ARGV[1])
if #keys >= tonumber(ARGV[2]) then
  return 0
end
redis.call('set', KEYS[1], ARGV[3], 'EX', ARGV[4])
return 1
"""


class RedisVoiceSessionManager:
    """Manages active voice sessions with Redis backend.

    Uses Redis hash storage for session data, enabling session sharing
    across multiple Uvicorn workers. Implements the same interface as
    VoiceSessionManager for compatibility.
    """

    def __init__(
        self,
        redis_url: str,
        max_sessions: int = 10,
        session_timeout: int = DEFAULT_SESSION_TTL,
        redis_session_ttl: int = DEFAULT_SESSION_TTL,
    ):
        """Initialize the Redis session manager.

        Args:
            redis_url: Redis connection URL
            max_sessions: Maximum concurrent sessions allowed
            session_timeout: Session timeout in seconds (for cleanup)
            redis_session_ttl: TTL for Redis keys in seconds
        """
        self.redis_url = redis_url
        self._max_sessions = max_sessions
        self._session_timeout = session_timeout
        self._redis_session_ttl = redis_session_ttl
        self._redis_client: redis.Redis | None = None
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None
        self._create_session_script_sha: str | None = None

    async def __aenter__(self) -> RedisVoiceSessionManager:
        """Enter async context manager and initialize Redis connection."""
        self._redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._redis_client.ping()
            logger.info(f"Redis session manager connected to {self.redis_url}")
            self._create_session_script_sha = await self._redis_client.script_load(
                _CREATE_SESSION_LUA
            )
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(
                f"Unable to connect to Redis at {self.redis_url}: {e}"
            ) from e
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager and close Redis connection."""
        if self._redis_client:
            await self._redis_client.aclose()
            logger.info("Redis session manager connection closed")
            self._redis_client = None

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{REDIS_KEY_PREFIX}:{session_id}"

    def _serialize_session(self, session: VoiceSession) -> str:
        """Serialize session to JSON string."""
        return json.dumps(session.to_dict())

    def _deserialize_session(self, _key: str, data: str) -> VoiceSession:
        """Deserialize session from JSON string."""
        data_dict = json.loads(data)
        return VoiceSession.from_dict(data_dict)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def create_session(self, context_id: str) -> VoiceSession:
        """Create a new voice session.

        Args:
            context_id: A2A context ID to associate with this session.

        Returns:
            The newly created ``VoiceSession``.

        Raises:
            RuntimeError: If the maximum number of concurrent sessions is reached.
            RuntimeError: If Redis client is not initialized.
        """
        if not self._redis_client or not self._create_session_script_sha:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        session_id = uuid4().hex
        session = VoiceSession(id=session_id, context_id=context_id)
        key = self._session_key(session_id)
        serialized_session = self._serialize_session(session)

        # Atomically check session count and create the new session using a Lua script.
        # This prevents a race condition across multiple workers.
        # The script counts keys matching the session pattern. This is acceptable for
        # a small number of max_sessions and avoids counter desynchronization.
        pattern = f"{REDIS_KEY_PREFIX}:*"
        success = await self._redis_client.evalsha(
            self._create_session_script_sha,
            1,  # Number of keys
            key,  # KEYS[1]
            pattern,  # ARGV[1]
            self._max_sessions,  # ARGV[2]
            serialized_session,  # ARGV[3]
            self._redis_session_ttl,  # ARGV[4]
        )

        if not success:
            raise RuntimeError(
                f"Maximum concurrent voice sessions ({self._max_sessions}) reached"
            )

        # The active count is not efficiently available here, so we omit it.
        logger.info(f"Voice session created: {session_id} (context={context_id})")
        return session

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Get a session by ID, or ``None`` if not found.

        Args:
            session_id: The session ID to look up.

        Returns:
            The session if found, None otherwise.
        """
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        key = self._session_key(session_id)
        data = await self._redis_client.get(key)

        if data is None:
            return None

        return self._deserialize_session(session_id, data)

    async def end_session(self, session_id: str) -> None:
        """Gracefully end a voice session.

        Marks the session as ``ended`` and removes it from Redis.

        Args:
            session_id: The session ID to end.
        """
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        async with self._lock:
            key = self._session_key(session_id)
            session_data = await self._redis_client.get(key)

            if session_data:
                session = self._deserialize_session(session_id, session_data)
                session.state = "ended"
                duration = session.duration_seconds
                logger.info(
                    f"Voice session ended: {session_id} (duration={duration:.1f}s)"
                )

            # Remove from Redis
            await self._redis_client.delete(key)
            logger.debug(f"Voice session removed from Redis: {session_id}")

    async def update_state(
        self,
        session_id: str,
        state: Literal["connecting", "active", "ending", "ended"],
    ) -> None:
        """Update the state of a session.

        Args:
            session_id: The session ID to update.
            state: The new state.
        """
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        async with self._lock:
            key = self._session_key(session_id)
            session_data = await self._redis_client.get(key)

            if session_data:
                session = self._deserialize_session(session_id, session_data)
                session.state = state
                # Update in Redis with refreshed TTL
                await self._redis_client.set(
                    key,
                    self._serialize_session(session),
                    ex=self._redis_session_ttl,
                )

    async def get_active_count(self) -> int:
        """Return the number of sessions that are not ended."""
        if not self._redis_client:
            return 0

        try:
            # Find all voice session keys
            pattern = f"{REDIS_KEY_PREFIX}:*"
            keys: list[str] = []
            async for key in self._redis_client.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                return 0

            # Get all session data and count non-ended
            count = 0
            for key in keys:
                data = await self._redis_client.get(key)
                if data:
                    session_id_from_key = key.split(":")[-1]
                    session = self._deserialize_session(session_id_from_key, data)
                    if session.state != "ended":
                        count += 1

            return count
        except redis.RedisError as e:
            logger.error(f"Error getting active session count: {e}")
            return 0

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    async def start_cleanup_loop(self) -> None:
        """Start the periodic session cleanup background task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Redis voice session cleanup loop started")

    async def stop_cleanup_loop(self) -> None:
        """Stop the cleanup background task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Redis voice session cleanup loop stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically expire sessions that exceed the timeout."""
        while True:
            try:
                await asyncio.sleep(30)  # check every 30s
                await self._expire_timed_out_sessions()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in Redis voice session cleanup loop")

    async def _expire_timed_out_sessions(self) -> None:
        """End sessions that have exceeded the configured timeout."""
        if not self._redis_client:
            return

        async with self._lock:
            expired: list[str] = []

            try:
                pattern = f"{REDIS_KEY_PREFIX}:*"
                async for key in self._redis_client.scan_iter(match=pattern):
                    data = await self._redis_client.get(key)
                    if data:
                        # Extract session_id from key for deserialization
                        session_id_from_key = key.split(":")[-1]
                        session = self._deserialize_session(session_id_from_key, data)
                        if (
                            session.state != "ended"
                            and session.duration_seconds > self._session_timeout
                        ):
                            session.state = "ended"
                            session_id = session.id
                            expired.append(session_id)
                            logger.warning(
                                f"Voice session timed out: {session_id} "
                                f"(duration={session.duration_seconds:.1f}s, "
                                f"limit={self._session_timeout}s)"
                            )
                            # Update in Redis
                            await self._redis_client.set(
                                key,
                                self._serialize_session(session),
                                ex=self._redis_session_ttl,
                            )

                # Remove expired sessions
                for session_id in expired:
                    await self._redis_client.delete(self._session_key(session_id))

            except redis.RedisError as e:
                logger.error(f"Error expiring timed out sessions: {e}")
