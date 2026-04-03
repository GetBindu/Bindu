"""Agent bridge between pipecat voice pipeline and Bindu A2A agents.

This custom pipecat ``FrameProcessor`` converts STT transcription frames
into chat messages, invokes the Bindu manifest's ``run()`` method, and
emits text frames that are consumed by the TTS service.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable

from bindu.server.workers.helpers.result_processor import ResultProcessor
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("bindu.voice.agent_bridge")

MAX_HISTORY_TURNS = 20


class AgentBridgeProcessor:
    """Bridges pipecat STT ↔ Bindu manifest ↔ pipecat TTS.

    Flow:
        1. Receives ``TranscriptionFrame`` from STT (user utterance).
        2. Appends to conversation history as ``{"role": "user", "content": text}``.
        3. Calls ``manifest.run(history)`` through the provided run function.
        4. Collects the result and appends as ``{"role": "assistant", "content": text}``.
        5. Emits a ``TextFrame`` for the downstream TTS service.
        6. Optionally sends real-time transcript events back to the WebSocket.
    """

    def __init__(
        self,
        manifest_run: Callable[..., Any],
        context_id: str,
        *,
        on_user_transcript: Callable[[str], Any] | None = None,
        on_agent_response: Callable[[str], Any] | None = None,
    ):
        """Initialize bridge callbacks and context for one voice session.

        Args:
            manifest_run: The ``manifest.run`` callable (accepts chat history list).
            context_id: A2A context ID for this voice session.
            on_user_transcript: Optional callback when user utterance is finalized.
            on_agent_response: Optional callback when agent produces a response.
        """
        self._manifest_run = manifest_run
        self._context_id = context_id
        self._on_user_transcript = on_user_transcript
        self._on_agent_response = on_agent_response
        self._conversation_history: list[dict[str, str]] = []
        self._max_history_messages = MAX_HISTORY_TURNS * 2
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._processing = False
        self._lock = asyncio.Lock()

    async def process_transcription(self, text: str) -> str | None:
        """Process a completed user transcription and get agent response.

        Args:
            text: Final transcription text from STT.

        Returns:
            Agent response text (or None if processing failed).
        """
        text = text.strip()
        if not text:
            return None

        async with self._lock:
            if self._processing:
                logger.warning("Skipping overlapping transcription while agent is busy")
                return None
            self._processing = True

        try:
            # Notify caller about the user transcript
            if self._on_user_transcript:
                self._safe_callback(self._on_user_transcript, text)

            # Add user message to history
            self._conversation_history.append({"role": "user", "content": text})
            self._trim_history()
            logger.debug(
                f"Voice user ({self._context_id}): {text[:80]}{'...' if len(text) > 80 else ''}"
            )

            # Invoke the agent
            response_text = await self._invoke_agent()

            if response_text:
                self._conversation_history.append(
                    {"role": "assistant", "content": response_text}
                )
                self._trim_history()
                logger.debug(
                    f"Voice agent ({self._context_id}): {response_text[:80]}{'...' if len(response_text) > 80 else ''}"
                )

                if self._on_agent_response:
                    self._safe_callback(self._on_agent_response, response_text)

            return response_text

        except Exception:
            logger.exception(
                f"Error processing voice transcription in {self._context_id}"
            )
            return None
        finally:
            async with self._lock:
                self._processing = False

    async def _invoke_agent(self) -> str | None:
        """Call manifest.run with the conversation history and return response text."""
        try:
            raw = self._manifest_run(list(self._conversation_history))
            result = await ResultProcessor.collect_results(raw)

            if result is None:
                return None

            # normalize_result handles dicts, objects, plain strings, etc.
            normalized = ResultProcessor.normalize_result(result)

            if isinstance(normalized, str):
                return normalized

            # Structured response — extract text content
            if isinstance(normalized, dict):
                # Handle {"content": "..."}, {"text": "..."}, {"state": "...", "message": ...}
                return (
                    normalized.get("content")
                    or normalized.get("text")
                    or normalized.get("message")
                    or str(normalized)
                )

            return str(normalized)

        except Exception:
            logger.exception("Agent invocation failed")
            return None

    @property
    def history(self) -> list[dict[str, str]]:
        """Return a read-only copy of the conversation history."""
        return list(self._conversation_history)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._conversation_history.clear()

    async def cleanup_background_tasks(self) -> None:
        """Cancel and await any background callback tasks."""
        if not self._background_tasks:
            return

        tasks = list(self._background_tasks)
        self._background_tasks.clear()

        for task in tasks:
            task.cancel()

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.error(f"Error while cleaning up voice callback task: {result}")

    def _trim_history(self) -> None:
        """Keep only the most recent conversation turns."""
        overflow = len(self._conversation_history) - self._max_history_messages
        if overflow > 0:
            turns_to_drop = max(1, (overflow + 1) // 2)
            del self._conversation_history[: turns_to_drop * 2]

    def _safe_callback(self, fn: Callable[..., Any], *args: Any) -> None:
        """Call a callback, tracking async tasks so they are not GC'd early."""
        try:
            result = fn(*args)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
        except Exception:
            logger.exception("Error in voice callback")
