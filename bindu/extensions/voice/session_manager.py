"""Voice session manager.

Tracks active voice sessions, enforces concurrency limits,
and runs a background cleanup task to expire timed-out sessions.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from bindu.utils.logging import get_logger

logger = get_logger("bindu.voice.session_manager")


@dataclass
class VoiceSession:
    """Represents an active voice conversation session."""

    id: str
    context_id: str
    task_id: str | None = None
    start_time: float = field(default_factory=time.monotonic)
    state: Literal["connecting", "active", "ending", "ended"] = "connecting"

    @property
    def duration_seconds(self) -> float:
        """Elapsed time since session started."""
        return time.monotonic() - self.start_time


class VoiceSessionManager:
    """Manages active voice sessions with lifecycle and cleanup.

    Enforces ``max_sessions`` concurrency and ``session_timeout``
    expiration through a periodic background task.
    """

    def __init__(self, max_sessions: int = 10, session_timeout: int = 300):
        self._sessions: dict[str, VoiceSession] = {}
        self._max_sessions = max_sessions
        self._session_timeout = session_timeout
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

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
        """
        async with self._lock:
            # Prune any already-ended sessions first
            self._sessions = {
                k: v for k, v in self._sessions.items() if v.state != "ended"
            }

            if len(self._sessions) >= self._max_sessions:
                raise RuntimeError(
                    f"Maximum concurrent voice sessions ({self._max_sessions}) reached"
                )

            session_id = uuid4().hex
            session = VoiceSession(id=session_id, context_id=context_id)
            self._sessions[session_id] = session

            logger.info(
                f"Voice session created: {session_id} (context={context_id}, "
                f"active={len(self._sessions)})"
            )
            return session

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Get a session by ID, or ``None`` if not found."""
        return self._sessions.get(session_id)

    async def end_session(self, session_id: str) -> None:
        """Gracefully end a voice session.

        Marks the session as ``ended`` and removes it from the active map.
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.state = "ended"
                logger.info(
                    f"Voice session ended: {session_id} "
                    f"(duration={session.duration_seconds:.1f}s)"
                )

    async def update_state(
        self,
        session_id: str,
        state: Literal["connecting", "active", "ending", "ended"],
    ) -> None:
        """Update the state of a session."""
        session = self._sessions.get(session_id)
        if session:
            session.state = state

    @property
    def active_count(self) -> int:
        """Number of sessions that are not ended."""
        return sum(1 for s in self._sessions.values() if s.state != "ended")

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    async def start_cleanup_loop(self) -> None:
        """Start the periodic session cleanup background task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Voice session cleanup loop started")

    async def stop_cleanup_loop(self) -> None:
        """Stop the cleanup background task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Voice session cleanup loop stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically expire sessions that exceed the timeout."""
        while True:
            try:
                await asyncio.sleep(30)  # check every 30 s
                await self._expire_timed_out_sessions()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in voice session cleanup loop")

    async def _expire_timed_out_sessions(self) -> None:
        """End sessions that have exceeded the configured timeout."""
        async with self._lock:
            expired: list[str] = []
            for sid, session in self._sessions.items():
                if (
                    session.state != "ended"
                    and session.duration_seconds > self._session_timeout
                ):
                    session.state = "ended"
                    expired.append(sid)
                    logger.warning(
                        f"Voice session timed out: {sid} "
                        f"(duration={session.duration_seconds:.1f}s, "
                        f"limit={self._session_timeout}s)"
                    )
            for sid in expired:
                self._sessions.pop(sid, None)
