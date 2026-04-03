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
    start_time: float = field(default_factory=time.time)
    state: Literal["connecting", "active", "ending", "ended"] = "connecting"

    def __post_init__(self) -> None:
        """Handle default start_time after initialization."""
        if self.start_time is None or self.start_time == 0:
            self.start_time = time.time()

    @property
    def duration_seconds(self) -> float:
        """Elapsed time since session started."""
        return max(0.0, time.time() - self.start_time)

    def to_dict(self) -> dict:
        """Serialize session to dictionary for Redis storage."""
        return {
            "id": self.id,
            "context_id": self.context_id,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VoiceSession:
        """Deserialize session from dictionary."""
        session_id = data.get("id")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError(
                "VoiceSession.id is required and must be a non-empty string"
            )

        context_id = data.get("context_id")
        if not isinstance(context_id, str) or not context_id.strip():
            raise ValueError(
                "VoiceSession.context_id is required and must be a non-empty string"
            )

        task_id = data.get("task_id")
        if task_id is not None and (
            not isinstance(task_id, str) or not task_id.strip()
        ):
            raise ValueError(
                "VoiceSession.task_id must be a non-empty string when provided"
            )

        start_time = data.get("start_time", time.time())
        if not isinstance(start_time, (int, float)) or isinstance(start_time, bool):
            raise ValueError("VoiceSession.start_time must be a numeric timestamp")

        state = data.get("state", "connecting")
        allowed_states = {"connecting", "active", "ending", "ended"}
        if state not in allowed_states:
            raise ValueError(
                f"VoiceSession.state must be one of {sorted(allowed_states)}; got {state!r}"
            )

        return cls(
            id=session_id,
            context_id=context_id,
            task_id=task_id,
            start_time=float(start_time),
            state=state,
        )


class VoiceSessionManager:
    """Manages active voice sessions with lifecycle and cleanup.

    Enforces ``max_sessions`` concurrency and ``session_timeout``
    expiration through a periodic background task.
    """

    def __init__(self, max_sessions: int = 10, session_timeout: int = 300):
        """Initialize in-memory voice session manager limits and cleanup state."""
        if (
            not isinstance(max_sessions, int)
            or isinstance(max_sessions, bool)
            or max_sessions <= 0
        ):
            raise ValueError("max_sessions must be a positive integer")
        if (
            not isinstance(session_timeout, int)
            or isinstance(session_timeout, bool)
            or session_timeout <= 0
        ):
            raise ValueError("session_timeout must be a positive integer")

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
            context_id: A2A context ID as a non-empty string.

        Returns:
            The newly created ``VoiceSession``.

        Raises:
            RuntimeError: If the maximum number of concurrent sessions is reached.
            ValueError: If context_id is not a non-empty string.
        """
        if not isinstance(context_id, str) or not context_id.strip():
            raise ValueError("context_id must be a non-empty string")

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
        async with self._lock:
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
        async with self._lock:
            if state == "ended":
                session = self._sessions.pop(session_id, None)
            else:
                session = self._sessions.get(session_id)
            if session:
                session.state = state

    async def get_active_count(self) -> int:
        """Return the number of sessions that are not ended."""
        async with self._lock:
            return sum(1 for s in self._sessions.values() if s.state != "ended")

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    async def start_cleanup_loop(self) -> None:
        """Start the periodic session cleanup background task."""
        async with self._lock:
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.info("Voice session cleanup loop started")

    async def stop_cleanup_loop(self) -> None:
        """Stop the cleanup background task."""
        task: asyncio.Task[None] | None = None
        async with self._lock:
            if self._cleanup_task is not None:
                task = self._cleanup_task
                self._cleanup_task = None

        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
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
