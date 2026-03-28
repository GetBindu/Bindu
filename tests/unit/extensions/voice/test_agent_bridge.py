"""Unit tests for AgentBridgeProcessor."""

import asyncio

import pytest

from bindu.extensions.voice.agent_bridge import AgentBridgeProcessor


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
