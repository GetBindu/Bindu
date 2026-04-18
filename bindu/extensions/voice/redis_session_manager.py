"""Redis-backed voice session manager.

Provides multi-worker compatible session storage using Redis as the backend,
enabling session lookup across Uvicorn workers.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlsplit
from typing import Literal, Any

import redis.asyncio as redis
from uuid import uuid4

from bindu.extensions.voice.session_manager import VoiceSession
from bindu.utils.logging import get_logger

logger = get_logger("bindu.voice.redis_session_manager")

# Constants
REDIS_KEY_PREFIX = "voice:sessions"
REDIS_ACTIVE_SET_KEY = f"{REDIS_KEY_PREFIX}:active"
DEFAULT_SESSION_TTL = 300  # seconds


_CREATE_SESSION_LUA = """
-- Atomically create a session if the active set is below the limit.
--
-- KEYS[1]: Active session set key.
-- KEYS[2]: The key for the new session to create.
-- ARGV[1]: The maximum number of sessions allowed.
-- ARGV[2]: The serialized session data to store.
-- ARGV[3]: The TTL for the new session key.
--
-- Returns: 1 if the session was created, 0 otherwise.
local active_members = redis.call('smembers', KEYS[1])
for _, member in ipairs(active_members) do
    if redis.call('exists', member) == 0 then
        redis.call('srem', KEYS[1], member)
    end
end

local active_count = redis.call('scard', KEYS[1])
if active_count >= tonumber(ARGV[1]) then
    return 0
end
redis.call('set', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('sadd', KEYS[1], KEYS[2])
return 1
"""


_UPDATE_SESSION_LUA = """
-- Atomically update the serialized session while keeping the TTL refreshed.
--
-- KEYS[1]: The session key to update.
-- ARGV[1]: The new state value.
-- ARGV[2]: The TTL for the session key.
--
-- Returns: 1 if the session existed and was updated, 0 otherwise.
local raw = redis.call('get', KEYS[1])
if not raw then
    return 0
end
local session = cjson.decode(raw)
session['state'] = ARGV[1]
redis.call('set', KEYS[1], cjson.encode(session), 'EX', ARGV[2])
return 1
"""


_DELETE_SESSION_LUA = """
-- Remove a session key and its active-set membership atomically.
--
-- KEYS[1]: Active session set key.
-- KEYS[2]: The session key to delete.
--
-- Returns: 1 if the session key existed, 0 otherwise.
local removed = redis.call('del', KEYS[2])
redis.call('srem', KEYS[1], KEYS[2])
return removed
"""


class RedisVoiceSessionManager:
    """Manages active voice sessions with Redis backend.

    Uses Redis string keys with JSON-serialized session data via SET/GET,
    enabling session sharing across multiple Uvicorn workers. Implements the
    same interface as VoiceSessionManager for compatibility.
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
        self._cleanup_task: asyncio.Task[None] | None = None
        self._create_session_script_sha: str | None = None
        self._update_session_script_sha: str | None = None
        self._delete_session_script_sha: str | None = None

    async def __aenter__(self) -> RedisVoiceSessionManager:
        """Enter async context manager and initialize Redis connection."""
        self._redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._redis_client.ping()
            logger.info(
                f"Redis session manager connected to {self._safe_redis_target()}"
            )
            self._create_session_script_sha = await self._redis_client.script_load(
                _CREATE_SESSION_LUA
            )
            self._update_session_script_sha = await self._redis_client.script_load(
                _UPDATE_SESSION_LUA
            )
            self._delete_session_script_sha = await self._redis_client.script_load(
                _DELETE_SESSION_LUA
            )
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            if self._redis_client is not None:
                await self._redis_client.aclose()
                self._redis_client = None
            raise ConnectionError(
                f"Unable to connect to Redis at {self._safe_redis_target()}: {e}"
            ) from e
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager and close Redis connection."""
        cleanup_task = self._cleanup_task
        if cleanup_task is not None:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            finally:
                self._cleanup_task = None

        redis_client = self._redis_client
        if redis_client is not None:
            await redis_client.aclose()
            logger.info("Redis session manager connection closed")
            self._redis_client = None

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{REDIS_KEY_PREFIX}:{session_id}"

    def _serialize_session(self, session: VoiceSession) -> str:
        """Serialize session to JSON string."""
        return json.dumps(session.to_dict())

    def _safe_redis_target(self) -> str:
        """Return a redacted Redis target for logs and errors."""
        parsed = urlsplit(self.redis_url)
        scheme = parsed.scheme or "redis"
        host = parsed.hostname or "unknown-host"
        port = f":{parsed.port}" if parsed.port else ""
        return f"{scheme}://***@{host}{port}"

    def _deserialize_session(self, _key: str, data: str) -> VoiceSession:
        """Deserialize session from JSON string."""
        data_dict = json.loads(data)
        return VoiceSession.from_dict(data_dict)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def create_session(
        self,
        context_id: str,
        *,
        session_token: str | None = None,
        session_token_expires_at: float | None = None,
    ) -> VoiceSession:
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
        session = VoiceSession(
            id=session_id,
            context_id=context_id,
            session_token=session_token,
            session_token_expires_at=session_token_expires_at,
        )
        key = self._session_key(session_id)
        serialized_session = self._serialize_session(session)

        # Atomically check session count and create the new session using a Lua script.
        # This prevents a race condition across multiple workers.
        success = await self._redis_client.evalsha(
            self._create_session_script_sha,
            2,
            REDIS_ACTIVE_SET_KEY,
            key,
            self._max_sessions,
            serialized_session,
            self._redis_session_ttl,
        )

        if not success:
            raise RuntimeError(
                f"Maximum concurrent voice sessions ({self._max_sessions}) reached"
            )

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

        try:
            key = self._session_key(session_id)
            data = await self._redis_client.get(key)

            if data is None:
                return None

            return self._deserialize_session(session_id, data)
        except redis.RedisError as e:
            logger.error(f"Error getting voice session {session_id}: {e}")
            return None

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

        if not self._delete_session_script_sha:
            raise RuntimeError(
                "Redis delete script not initialized. Use async context manager."
            )

        key = self._session_key(session_id)
        session_data = await self._redis_client.get(key)

        if session_data:
            session = self._deserialize_session(session_id, session_data)
            duration = session.duration_seconds
            logger.info(f"Voice session ended: {session_id} (duration={duration:.1f}s)")

        await self._redis_client.evalsha(
            self._delete_session_script_sha,
            2,
            REDIS_ACTIVE_SET_KEY,
            key,
        )
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

        key = self._session_key(session_id)
        if not self._update_session_script_sha:
            raise RuntimeError(
                "Redis update script not initialized. Use async context manager."
            )

        success = await self._redis_client.evalsha(
            self._update_session_script_sha,
            1,
            key,
            state,
            self._redis_session_ttl,
        )
        if not success:
            logger.debug(f"Session missing during update_state: {session_id}")

    async def get_active_count(self) -> int:
        """Return the number of sessions that are not ended."""
        if not self._redis_client:
            return 0

        try:
            members = await self._redis_client.smembers(REDIS_ACTIVE_SET_KEY)
            if not members:
                return 0

            pipeline = self._redis_client.pipeline()
            for key in members:
                pipeline.get(key)
            values = await pipeline.execute()

            count = 0
            stale_members: list[str] = []
            for key, data in zip(members, values):
                if data:
                    session = self._deserialize_session(key.split(":")[-1], data)
                    if session.state != "ended":
                        count += 1
                else:
                    stale_members.append(key)

            if stale_members:
                await self._redis_client.srem(REDIS_ACTIVE_SET_KEY, *stale_members)

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

        try:
            expired: list[str] = []
            members = await self._redis_client.smembers(REDIS_ACTIVE_SET_KEY)

            for key in members:
                data = await self._redis_client.get(key)
                if not data:
                    expired.append(key)
                    continue

                session = self._deserialize_session(key.split(":")[-1], data)
                if (
                    session.state != "ended"
                    and session.duration_seconds > self._session_timeout
                ):
                    session_id = session.id
                    expired.append(key)
                    logger.warning(
                        f"Voice session timed out: {session_id} "
                        f"(duration={session.duration_seconds:.1f}s, "
                        f"limit={self._session_timeout}s)"
                    )

            for key in expired:
                if self._delete_session_script_sha:
                    await self._redis_client.evalsha(
                        self._delete_session_script_sha,
                        2,
                        REDIS_ACTIVE_SET_KEY,
                        key,
                    )
                else:
                    await self._redis_client.delete(key)
                    await self._redis_client.srem(REDIS_ACTIVE_SET_KEY, key)

        except redis.RedisError as e:
            logger.error(f"Error expiring timed out sessions: {e}")
