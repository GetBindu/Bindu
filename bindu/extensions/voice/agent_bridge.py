"""Agent bridge between pipecat voice pipeline and Bindu A2A agents.

This custom pipecat ``FrameProcessor`` converts STT transcription frames
into chat messages, invokes the Bindu manifest's ``run()`` method, and
emits text frames that are consumed by the TTS service.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Callable, AsyncIterator

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TextFrame,
    InterruptionFrame,
    EndFrame,
    ErrorFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from bindu.server.workers.helpers.result_processor import ResultProcessor
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("bindu.voice.agent_bridge")

MAX_HISTORY_TURNS = 20
DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS = 10.0
DEFAULT_TOTAL_RESPONSE_TIMEOUT_SECONDS = 30.0
DEFAULT_THINKING_TEXT = "One moment."
DEFAULT_TIMEOUT_FALLBACK_TEXT = "Sorry — I’m having trouble responding right now."


class AgentBridgeProcessor(FrameProcessor):
    """Bridges pipecat STT ↔ Bindu manifest ↔ pipecat TTS.

    Flow:
        1. Receives ``TranscriptionFrame`` from STT (user utterance).
        2. Appends to conversation history as ``{"role": "user", "content": text}``.
        3. Calls ``manifest.run(history)`` through the provided run function in a task.
        4. Collects the result and appends as ``{"role": "assistant", "content": text}``.
        5. Emits a ``TextFrame`` for the downstream TTS service.
        6. Optionally sends real-time transcript events back to the WebSocket.
    """

    def __init__(
        self,
        manifest_run: Callable[..., Any],
        context_id: str,
        *,
        allow_interruptions: bool = True,
        first_token_timeout_seconds: float = DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS,
        total_response_timeout_seconds: float = DEFAULT_TOTAL_RESPONSE_TIMEOUT_SECONDS,
        on_state_change: Callable[[str], Any] | None = None,
        on_user_transcript: Callable[[str], Any] | None = None,
        on_agent_response: Callable[[str], Any] | None = None,
        on_agent_transcript: Callable[[str, bool], Any] | None = None,
    ):
        """Initialize bridge callbacks and context for one voice session."""
        super().__init__()
        self._manifest_run = manifest_run
        self._context_id = context_id
        self._allow_interruptions = bool(allow_interruptions)
        self._first_token_timeout_seconds = float(first_token_timeout_seconds)
        self._total_response_timeout_seconds = float(total_response_timeout_seconds)
        self._on_state_change = on_state_change
        self._on_user_transcript = on_user_transcript
        self._on_agent_response = on_agent_response
        self._on_agent_transcript = on_agent_transcript
        self._conversation_history: list[dict[str, str]] = []
        self._max_history_messages = MAX_HISTORY_TURNS * 2
        self._background_tasks: set[asyncio.Task[Any]] = set()

        self._current_agent_task: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming pipecat frames."""
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                await self._handle_user_utterance(text)
        elif isinstance(frame, InterruptionFrame):
            if not self._allow_interruptions:
                return
            logger.info("Interruption frame received; cancelling current agent task...")
            await self._cancel_current_agent_task()
            # Propagate interruption downstream so TTS/services can stop immediately.
            await self.push_frame(frame)
            self._set_state("listening")
        elif isinstance(frame, EndFrame):
            # Session is ending, cleanup background tasks
            await self.cleanup_background_tasks()
        elif isinstance(frame, ErrorFrame):
            logger.error(f"Error frame received in pipeline: {frame.error}")

    async def process_transcription(self, text: str, *, emit_frames: bool = False) -> str | None:
        """Process a user transcription and return the agent response.

        This is a convenience helper used by unit tests and non-pipeline callers.
        It updates the conversation history and executes the agent handler
        synchronously (no background task). When ``emit_frames=True``, it also
        streams partial ``TextFrame`` deltas to downstream processors (TTS).
        """
        cleaned = text.strip()
        if not cleaned:
            return None

        if self._allow_interruptions:
            await self._interrupt()
        else:
            await self._cancel_current_agent_task()

        if self._on_user_transcript:
            self._safe_callback(self._on_user_transcript, cleaned)

        self._conversation_history.append({"role": "user", "content": cleaned})
        self._trim_history()

        response_text = await self._invoke_agent_streaming(emit_frames=emit_frames)
        if response_text:
            self._conversation_history.append(
                {"role": "assistant", "content": response_text}
            )
            self._trim_history()
            if self._on_agent_response:
                self._safe_callback(self._on_agent_response, response_text)
            return response_text

        # Keep history consistent when invocation fails or yields no response.
        if self._conversation_history:
            last = self._conversation_history[-1]
            if last.get("role") == "user" and last.get("content") == cleaned:
                self._conversation_history.pop()
                self._trim_history()
        return None

    async def _handle_user_utterance(self, text: str) -> None:
        """Process a completed user transcription and get agent response."""
        # Cancel any running agent task
        if self._allow_interruptions:
            await self._interrupt()
        else:
            await self._cancel_current_agent_task()

        # Notify caller about the user transcript
        if self._on_user_transcript:
            self._safe_callback(self._on_user_transcript, text)

        # Add user message to history
        self._conversation_history.append({"role": "user", "content": text})
        self._trim_history()
        logger.debug(
            f"Voice user ({self._context_id}): {text[:80]}{'...' if len(text) > 80 else ''}"
        )

        # Start a new task to invoke the agent
        self._current_agent_task = asyncio.create_task(self._invoke_and_emit(text))

    async def _interrupt(self) -> None:
        """Cancel the in-flight agent task and propagate interruption downstream."""
        if self._current_agent_task and not self._current_agent_task.done():
            self._current_agent_task.cancel()
            # Tell downstream processors (esp. TTS) to stop immediately.
            try:
                await self.push_frame(InterruptionFrame())
            except Exception:
                logger.exception("Failed to push InterruptionFrame downstream")
            try:
                await self._current_agent_task
            except asyncio.CancelledError:
                pass

    async def _invoke_and_emit(self, user_text: str):
        """Invoke agent and emit text frames."""
        try:
            response_text = await self._invoke_agent_streaming(emit_frames=True)
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
            elif self._conversation_history:
                # Keep history consistent when invocation fails or yields no response.
                last = self._conversation_history[-1]
                if last.get("role") == "user" and last.get("content") == user_text:
                    self._conversation_history.pop()
                    self._trim_history()
        except asyncio.CancelledError:
            # Handle cancellation (interruption)
            logger.debug("Agent task was cancelled.")
            self._set_state("listening")
            # Remove the last user text if agent didn't finish responding
            if self._conversation_history:
                last = self._conversation_history[-1]
                if last.get("role") == "user" and last.get("content") == user_text:
                    self._conversation_history.pop()
            raise
        except Exception:
            if self._conversation_history:
                last = self._conversation_history[-1]
                if last.get("role") == "user" and last.get("content") == user_text:
                    self._conversation_history.pop()
                    self._trim_history()
            logger.exception(
                f"Error processing voice transcription in {self._context_id}"
            )

    async def _invoke_agent_streaming(self, *, emit_frames: bool) -> str | None:
        """Invoke the agent handler and optionally stream deltas as TextFrames."""
        try:
            raw = self._manifest_run(list(self._conversation_history))
            if inspect.isawaitable(raw) and not hasattr(raw, "__anext__"):
                raw = await raw

            streamed_text = ""
            last_emitted = ""
            started_speaking = False

            async def _consume_chunk(chunk_text: str) -> None:
                nonlocal streamed_text, last_emitted, started_speaking
                if not chunk_text:
                    return

                # Some streaming handlers yield cumulative text. Emit only the delta.
                delta = self._trim_overlap_text(last_emitted, chunk_text)
                if not delta:
                    last_emitted = chunk_text
                    return

                if emit_frames:
                    if not started_speaking:
                        started_speaking = True
                        self._set_state("agent-speaking")
                    if self._on_agent_transcript:
                        self._safe_callback(self._on_agent_transcript, delta, False)
                    await self.push_frame(TextFrame(delta))

                streamed_text = self._append_text(streamed_text, delta)
                last_emitted = chunk_text

            chunks = self._iter_text_chunks(raw)
            try:
                async with asyncio.timeout(self._total_response_timeout_seconds):
                    if emit_frames:
                        try:
                            first_task = asyncio.create_task(anext(chunks))
                            timeout_seconds = max(0.0, self._first_token_timeout_seconds)
                            if timeout_seconds > 0:
                                done, _pending = await asyncio.wait(
                                    {first_task}, timeout=timeout_seconds
                                )
                                if not done:
                                    # TTS filler so the agent doesn't feel "dead air".
                                    await self.push_frame(TextFrame(DEFAULT_THINKING_TEXT))
                            first = await first_task
                        except StopAsyncIteration:
                            return None

                        await _consume_chunk(first)

                    async for chunk_text in chunks:
                        await _consume_chunk(chunk_text)
            except TimeoutError:
                if emit_frames:
                    self._set_state("error")
                    fallback = DEFAULT_TIMEOUT_FALLBACK_TEXT
                    if self._on_agent_transcript:
                        self._safe_callback(self._on_agent_transcript, fallback, True)
                    await self.push_frame(TextFrame(fallback))
                    self._set_state("listening")
                    return fallback
                return None

            if emit_frames:
                if streamed_text and self._on_agent_transcript:
                    self._safe_callback(self._on_agent_transcript, streamed_text, True)
                self._set_state("listening")
            return streamed_text or None

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Agent invocation failed")
            if emit_frames:
                self._set_state("error")
            return None

    async def _cancel_current_agent_task(self) -> None:
        if self._current_agent_task and not self._current_agent_task.done():
            self._current_agent_task.cancel()
            try:
                await self._current_agent_task
            except asyncio.CancelledError:
                pass

    async def _iter_text_chunks(self, raw_results: Any) -> AsyncIterator[str]:
        """Yield normalized text chunks from sync/async results."""
        if raw_results is None:
            return

        # Async generator / async iterator
        if hasattr(raw_results, "__anext__"):
            async for item in raw_results:
                text = self._extract_text(item)
                if text:
                    yield text
            return

        # Sync generator / iterator
        if hasattr(raw_results, "__next__"):
            for item in raw_results:  # type: ignore[assignment]
                text = self._extract_text(item)
                if text:
                    yield text
            return

        # Direct return
        text = self._extract_text(raw_results)
        if text:
            yield text

    def _extract_text(self, value: Any) -> str | None:
        """Extract text from handler output chunks."""
        if value is None:
            return None

        normalized = ResultProcessor.normalize_result(value)

        if normalized is None:
            return None
        if isinstance(normalized, str):
            return normalized
        if isinstance(normalized, dict):
            content = normalized.get("content") or normalized.get("text") or normalized.get(
                "message"
            )
            if isinstance(content, str):
                return content
            # Dict with state but no content: ignore for voice TTS.
            if "state" in normalized:
                return None
            return str(normalized)
        return str(normalized)

    def _append_text(self, existing: str, delta: str) -> str:
        if not existing:
            return delta.strip()
        if not delta:
            return existing
        if existing.endswith((" ", "\n")) or delta.startswith((" ", "\n")):
            return f"{existing}{delta}".strip()
        return f"{existing} {delta}".strip()

    def _trim_overlap_text(self, previous: str, current: str) -> str:
        """Remove token overlap when current repeats previous suffix."""
        prev = previous.strip()
        curr = current.strip()
        if not prev:
            return curr
        if prev == curr:
            return ""

        prev_tokens = prev.split()
        curr_tokens = curr.split()

        max_overlap = min(len(prev_tokens), len(curr_tokens))
        for overlap in range(max_overlap, 0, -1):
            if prev_tokens[-overlap:] == curr_tokens[:overlap]:
                return " ".join(curr_tokens[overlap:]).strip()

        return curr

    @property
    def history(self) -> list[dict[str, str]]:
        """Return a read-only copy of the conversation history."""
        return list(self._conversation_history)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._conversation_history.clear()

    async def cleanup_background_tasks(self) -> None:
        """Cancel and await any background callback tasks."""
        await self._cancel_current_agent_task()
            
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

    def _set_state(self, state: str) -> None:
        if self._on_state_change:
            self._safe_callback(self._on_state_change, state)
