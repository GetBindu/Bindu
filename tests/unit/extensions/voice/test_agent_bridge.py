"""Unit tests for AgentBridgeProcessor."""

import asyncio

import pytest
from unittest.mock import AsyncMock

from bindu.extensions.voice.agent_bridge import AgentBridgeProcessor
from pipecat.frames.frames import TranscriptionFrame, InterruptionFrame
from pipecat.processors.frame_processor import FrameDirection


class TestAgentBridgeProcessor:
    """Test the voice → agent → TTS bridge."""

    @pytest.fixture
    def sync_manifest_run(self):
        """A manifest.run that returns a plain string."""

        def run(history):
            last = history[-1]["content"] if history else ""
            return f"Echo: {last}"

        return run

    @pytest.fixture
    def async_gen_manifest_run(self):
        """A manifest.run that returns an async generator."""

        async def run(history):
            last = history[-1]["content"] if history else ""
            yield f"Streamed: {last}"

        return run

    @pytest.fixture
    def bridge(self, sync_manifest_run):
        return AgentBridgeProcessor(
            manifest_run=sync_manifest_run,
            context_id="test-ctx",
        )

    @pytest.mark.asyncio
    async def test_process_transcription_basic(self, bridge):
        result = await bridge.process_transcription("Hello agent")
        assert result == "Echo: Hello agent"

    @pytest.mark.asyncio
    async def test_empty_transcription_returns_none(self, bridge):
        result = await bridge.process_transcription("")
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_transcription_returns_none(self, bridge):
        result = await bridge.process_transcription("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_conversation_history_builds(self, bridge):
        await bridge.process_transcription("Hello")
        await bridge.process_transcription("How are you?")
        history = bridge.history
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Echo: Hello"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "How are you?"
        assert history[3]["role"] == "assistant"
        assert history[3]["content"] == "Echo: How are you?"

    @pytest.mark.asyncio
    async def test_clear_history(self, bridge):
        await bridge.process_transcription("Hello")
        assert len(bridge.history) > 0
        bridge.clear_history()
        assert len(bridge.history) == 0

    @pytest.mark.asyncio
    async def test_callbacks_called(self):
        user_texts = []
        agent_texts = []

        def run(history):
            return "Agent response"

        bridge = AgentBridgeProcessor(
            manifest_run=run,
            context_id="ctx",
            on_user_transcript=lambda t: user_texts.append(t),
            on_agent_response=lambda t: agent_texts.append(t),
        )
        await bridge.process_transcription("Hello")
        assert user_texts == ["Hello"]
        assert agent_texts == ["Agent response"]

    @pytest.mark.asyncio
    async def test_agent_transcript_deltas_emitted_when_emit_frames_true(self):
        deltas: list[tuple[str, bool]] = []

        async def run(history):
            yield "hello this"
            yield "hello this is"
            yield "hello this is agent"

        bridge = AgentBridgeProcessor(
            manifest_run=run,
            context_id="ctx",
            on_agent_transcript=lambda text, is_final: deltas.append((text, is_final)),
        )
        bridge.push_frame = AsyncMock()

        result = await bridge.process_transcription("Hi", emit_frames=True)
        assert result == "hello this is agent"
        assert deltas[0] == ("hello this", False)
        assert deltas[1] == ("is", False)
        assert deltas[2] == ("agent", False)
        assert deltas[-1] == ("hello this is agent", True)

    @pytest.mark.asyncio
    async def test_cumulative_chunks_with_punctuation_do_not_duplicate(self):
        deltas: list[tuple[str, bool]] = []

        async def run(history):
            yield "Hello!"
            yield "Hello! How can I assist"
            yield "Hello! How can I assist you today?"

        bridge = AgentBridgeProcessor(
            manifest_run=run,
            context_id="ctx",
            on_agent_transcript=lambda text, is_final: deltas.append((text, is_final)),
        )
        bridge.push_frame = AsyncMock()

        result = await bridge.process_transcription("Hi", emit_frames=True)
        assert result == "Hello! How can I assist you today?"

        partials = [text for text, is_final in deltas if not is_final]
        assert partials == ["Hello!", "How can I assist", "you today?"]
        assert deltas[-1] == ("Hello! How can I assist you today?", True)

    @pytest.mark.asyncio
    async def test_new_transcription_interrupts_downstream_when_allow_interruptions(
        self,
    ):
        first_started = asyncio.Event()
        unblock_first = asyncio.Event()

        async def run(history):
            if history and history[-1]["content"] == "first":
                first_started.set()
                await unblock_first.wait()
                return "done"
            return "ok"

        bridge = AgentBridgeProcessor(
            manifest_run=run, context_id="ctx", allow_interruptions=True
        )
        bridge.push_frame = AsyncMock()

        await bridge.process_frame(
            TranscriptionFrame("first", user_id="u", timestamp=0.0),
            direction=FrameDirection.DOWNSTREAM,
        )
        await asyncio.wait_for(first_started.wait(), timeout=1)

        await bridge.process_frame(
            TranscriptionFrame("second", user_id="u", timestamp=1.0),
            direction=FrameDirection.DOWNSTREAM,
        )

        # Should have pushed an interruption downstream due to barge-in.
        assert any(
            isinstance(call.args[0], InterruptionFrame)
            for call in bridge.push_frame.await_args_list
            if call.args
        )

        unblock_first.set()

    @pytest.mark.asyncio
    async def test_agent_timeout_returns_fallback_and_emits_tts_filler(self):
        async def run(history):
            await asyncio.sleep(0.05)
            yield "late response"

        bridge = AgentBridgeProcessor(
            manifest_run=run,
            context_id="ctx",
            allow_interruptions=True,
            first_token_timeout_seconds=0.01,
            total_response_timeout_seconds=0.02,
        )
        bridge.push_frame = AsyncMock()

        result = await bridge.process_transcription("Hello", emit_frames=True)
        assert isinstance(result, str)
        assert "Sorry" in result

        # First filler, then fallback.
        assert bridge.push_frame.await_count >= 2

    @pytest.mark.asyncio
    async def test_agent_error_returns_none(self):
        def bad_run(history):
            raise RuntimeError("agent crashed")

        bridge = AgentBridgeProcessor(
            manifest_run=bad_run,
            context_id="ctx",
        )
        result = await bridge.process_transcription("Hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_async_generator_manifest(self, async_gen_manifest_run):
        bridge = AgentBridgeProcessor(
            manifest_run=async_gen_manifest_run,
            context_id="ctx",
        )
        result = await bridge.process_transcription("Test input")
        assert result == "Streamed: Test input"

    @pytest.mark.asyncio
    async def test_dict_response_extraction(self):
        def run(history):
            return {"content": "Dict response"}

        bridge = AgentBridgeProcessor(manifest_run=run, context_id="ctx")
        result = await bridge.process_transcription("Hello")
        assert result == "Dict response"

    @pytest.mark.asyncio
    async def test_none_response(self):
        def run(history):
            return None

        bridge = AgentBridgeProcessor(manifest_run=run, context_id="ctx")
        result = await bridge.process_transcription("Hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_history_is_trimmed_to_recent_turns(self):
        def run(history):
            return f"Echo: {history[-1]['content']}"

        bridge = AgentBridgeProcessor(manifest_run=run, context_id="ctx")

        for index in range(25):
            await bridge.process_transcription(f"message {index}")

        history = bridge.history
        total_messages = 50
        overflow = max(0, total_messages - bridge._max_history_messages)
        turns_to_drop = max(1, (overflow + 1) // 2) if overflow else 0
        expected_len = total_messages - (turns_to_drop * 2)
        expected_first_index = turns_to_drop
        assert len(history) == expected_len
        assert history[0]["content"] == f"message {expected_first_index}"
        assert history[-1]["content"] == "Echo: message 24"

    @pytest.mark.asyncio
    async def test_async_callbacks_are_tracked_until_completion(self):
        event = asyncio.Event()
        user_texts: list[str] = []

        async def on_user(text: str) -> None:
            await asyncio.sleep(0)
            user_texts.append(text)
            event.set()

        bridge = AgentBridgeProcessor(
            manifest_run=lambda history: "Agent response",
            context_id="ctx",
            on_user_transcript=on_user,
        )

        await bridge.process_transcription("Hello")
        await asyncio.wait_for(event.wait(), timeout=1)
        await asyncio.sleep(0)

        assert user_texts == ["Hello"]
        assert bridge._background_tasks == set()
