"""Comprehensive tests for the streaming (message/stream) implementation.

Tests cover the refactored stream_message handler including:
- Full streaming lifecycle (working → chunks → last_chunk → completed)
- Worker pipeline integration (history building, system prompt)
- Payment context forwarding and settlement
- Error handling and failure states (including storage error resilience)
- Different result types (async gen, sync gen, direct return)
- SSE event format validation against A2A protocol types
- Push notification registration
- Telemetry span and metrics
- Edge cases (empty streams, no workers, None manifest result)
"""

import json
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from bindu.common.protocol.types import (
    StreamMessageRequest,
)
from bindu.server.handlers.message_handlers import (
    MessageHandlers,
    _build_artifact_event,
    _build_status_event,
    _format_sse_event,
)
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.mocks import MockAgent, MockManifest
from tests.utils import create_test_message


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    """Create fresh in-memory storage."""
    return InMemoryStorage()


@pytest_asyncio.fixture
async def scheduler():
    """Create in-memory scheduler."""
    sched = InMemoryScheduler()
    async with sched:
        yield sched


def _make_stream_request(
    text: str = "Hello, stream!",
    context_id: Any = None,
    configuration: dict | None = None,
    metadata: dict | None = None,
) -> StreamMessageRequest:
    """Build a StreamMessageRequest for testing."""
    msg = create_test_message(text=text, context_id=context_id or uuid4())
    if metadata:
        msg["metadata"] = metadata

    params: dict[str, Any] = {"message": msg}
    if configuration:
        params["configuration"] = configuration

    return cast(
        StreamMessageRequest,
        {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/stream",
            "params": params,
        },
    )


def _make_worker(**overrides):
    """Create a mock worker with sensible defaults.

    Uses public method names (build_complete_message_history, settle_payment)
    matching the ManifestWorker public API.
    """
    worker = MagicMock()
    worker.build_complete_message_history = overrides.get(
        "build_complete_message_history",
        AsyncMock(return_value=overrides.get("history", [])),
    )
    worker.settle_payment = overrides.get(
        "settle_payment",
        AsyncMock(return_value=overrides.get("settle_result", {})),
    )
    return worker


def _make_handlers(
    storage: InMemoryStorage,
    scheduler: InMemoryScheduler,
    manifest: Any = None,
    workers: list | None = None,
    push_manager: Any = None,
) -> MessageHandlers:
    """Create MessageHandlers with test dependencies."""
    import uuid as _uuid

    return MessageHandlers(
        scheduler=scheduler,
        storage=storage,
        manifest=manifest,
        workers=workers,
        context_id_parser=lambda cid: cid if cid else _uuid.uuid4(),
        push_manager=push_manager,
    )


async def _collect_sse_events(response) -> list[dict]:
    """Collect all SSE events from a StreamingResponse."""
    events = []
    async for chunk in response.body_iterator:
        if chunk.startswith("data: "):
            json_str = chunk[len("data: ") :].strip()
            if json_str:
                events.append(json.loads(json_str))
    return events


# ---------------------------------------------------------------------------
# SSE Event Builder Tests
# ---------------------------------------------------------------------------


class TestSSEEventBuilders:
    """Test the SSE event builder helper functions."""

    def test_build_status_event_working(self):
        """Test status event for working state."""
        task_id = uuid4()
        ctx_id = uuid4()
        event = _build_status_event(task_id, ctx_id, "working", final=False)

        assert event["kind"] == "status-update"
        assert event["task_id"] == str(task_id)
        assert event["context_id"] == str(ctx_id)
        assert event["status"]["state"] == "working"
        assert event["final"] is False
        assert "error" not in event
        assert "timestamp" in event["status"]

    def test_build_status_event_completed(self):
        """Test status event for completed state."""
        event = _build_status_event(uuid4(), uuid4(), "completed", final=True)

        assert event["status"]["state"] == "completed"
        assert event["final"] is True

    def test_build_status_event_failed_with_error(self):
        """Test status event for failed state includes error."""
        event = _build_status_event(
            uuid4(), uuid4(), "failed", final=True, error="Something broke"
        )

        assert event["status"]["state"] == "failed"
        assert event["final"] is True
        assert event["error"] == "Something broke"

    def test_build_artifact_event(self):
        """Test artifact event construction."""
        task_id = uuid4()
        ctx_id = uuid4()
        event = _build_artifact_event(
            task_id, ctx_id, "art-123", "Hello chunk", append=True, last_chunk=False
        )

        assert event["kind"] == "artifact-update"
        assert event["task_id"] == str(task_id)
        assert event["artifact"]["artifact_id"] == "art-123"
        assert event["artifact"]["parts"][0]["text"] == "Hello chunk"
        assert event["append"] is True
        assert event["last_chunk"] is False

    def test_build_artifact_event_last_chunk(self):
        """Test artifact event marks last chunk correctly."""
        event = _build_artifact_event(
            uuid4(), uuid4(), "art-1", "final", append=False, last_chunk=True
        )

        assert event["append"] is False
        assert event["last_chunk"] is True

    def test_format_sse_event(self):
        """Test SSE string formatting."""
        result = _format_sse_event({"kind": "test", "value": 42})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        parsed = json.loads(result[len("data: ") :].strip())
        assert parsed["kind"] == "test"
        assert parsed["value"] == 42


# ---------------------------------------------------------------------------
# Streaming Lifecycle Tests
# ---------------------------------------------------------------------------


class TestStreamingLifecycle:
    """Test the full streaming lifecycle."""

    @pytest.mark.asyncio
    async def test_stream_happy_path_sync_generator(self, storage, scheduler):
        """Test successful streaming with a sync generator (default MockManifest)."""
        manifest = MockManifest(agent_fn=MockAgent(response="streamed result"))
        worker = _make_worker(
            history=[{"role": "user", "content": "Hello"}],
        )

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        request = _make_stream_request()
        response = await handlers.stream_message(request)

        # Verify response is StreamingResponse
        assert response.media_type == "text/event-stream"

        events = await _collect_sse_events(response)

        # Should have: working status, artifact chunk(s), last_chunk marker, completed status
        assert len(events) >= 4
        assert events[0]["kind"] == "status-update"
        assert events[0]["status"]["state"] == "working"
        assert events[0]["final"] is False

        # Middle events should be artifact updates
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        content_events = [e for e in artifact_events if not e["last_chunk"]]
        assert len(content_events) >= 1
        assert content_events[0]["artifact"]["parts"][0]["text"] == "streamed result"

        # Last event should be completed status
        assert events[-1]["kind"] == "status-update"
        assert events[-1]["status"]["state"] == "completed"
        assert events[-1]["final"] is True

    @pytest.mark.asyncio
    async def test_stream_updates_storage_on_completion(self, storage, scheduler):
        """Test that streaming persists artifacts and messages to storage."""
        manifest = MockManifest(agent_fn=MockAgent(response="final answer"))
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        request = _make_stream_request()
        response = await handlers.stream_message(request)

        # Consume the stream
        await _collect_sse_events(response)

        # Verify storage was updated with completed state and artifacts
        tasks = await storage.list_tasks()
        assert len(tasks) == 1
        task = tasks[0]
        assert task["status"]["state"] == "completed"
        assert "artifacts" in task
        assert len(task["artifacts"]) > 0
        assert "history" in task
        # Should have user message + agent response message
        assert len(task["history"]) >= 2

    @pytest.mark.asyncio
    async def test_stream_with_async_generator(self, storage, scheduler):
        """Test streaming with an async generator response."""
        manifest = MockManifest()

        async def async_gen_run(message_history):
            for word in ["Hello", " ", "World"]:
                yield word

        manifest.run = async_gen_run

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        request = _make_stream_request()
        response = await handlers.stream_message(request)
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        content_events = [e for e in artifact_events if not e["last_chunk"]]
        assert len(content_events) == 3
        texts = [e["artifact"]["parts"][0]["text"] for e in content_events]
        assert texts == ["Hello", " ", "World"]

        # All chunks should share the same artifact_id
        artifact_ids = {e["artifact"]["artifact_id"] for e in artifact_events}
        assert len(artifact_ids) == 1

    @pytest.mark.asyncio
    async def test_stream_with_direct_return(self, storage, scheduler):
        """Test streaming with a non-generator direct return value."""
        manifest = MockManifest()
        manifest.run = lambda history: "Direct response"

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        request = _make_stream_request()
        response = await handlers.stream_message(request)
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        assert len(artifact_events) == 1
        assert artifact_events[0]["artifact"]["parts"][0]["text"] == "Direct response"
        assert artifact_events[0]["last_chunk"] is True

    @pytest.mark.asyncio
    async def test_stream_consistent_artifact_id_across_chunks(
        self, storage, scheduler
    ):
        """Test that all chunks share a single artifact_id for client reassembly."""
        manifest = MockManifest()

        def gen_run(history):
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        manifest.run = gen_run

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        ids = {e["artifact"]["artifact_id"] for e in artifact_events}
        assert len(ids) == 1, "All chunks must share same artifact_id"

    @pytest.mark.asyncio
    async def test_stream_generator_emits_last_chunk_marker(self, storage, scheduler):
        """Test that generator paths emit a final last_chunk=True marker event."""
        manifest = MockManifest()

        def gen_run(history):
            yield "chunk1"
            yield "chunk2"

        manifest.run = gen_run
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        # Last artifact event should be the last_chunk marker
        assert artifact_events[-1]["last_chunk"] is True
        assert artifact_events[-1]["artifact"]["parts"][0]["text"] == ""
        # Earlier chunks should not be last_chunk
        for evt in artifact_events[:-1]:
            assert evt["last_chunk"] is False

    @pytest.mark.asyncio
    async def test_stream_async_generator_emits_last_chunk_marker(
        self, storage, scheduler
    ):
        """Test that async generator paths also emit last_chunk=True marker."""
        manifest = MockManifest()

        async def async_gen_run(history):
            yield "a"
            yield "b"

        manifest.run = async_gen_run
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        assert artifact_events[-1]["last_chunk"] is True


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestStreamingErrors:
    """Test error handling during streaming."""

    @pytest.mark.asyncio
    async def test_stream_agent_error_yields_failed_event(self, storage, scheduler):
        """Test that agent exceptions produce a failed status event."""
        manifest = MockManifest(
            agent_fn=MockAgent(response="boom", response_type="error")
        )
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        # Should have working status then failed status
        status_events = [e for e in events if e["kind"] == "status-update"]
        assert status_events[0]["status"]["state"] == "working"
        assert status_events[-1]["status"]["state"] == "failed"
        assert status_events[-1]["final"] is True
        assert "error" in status_events[-1]

        # Verify storage reflects failure
        tasks = await storage.list_tasks()
        assert tasks[0]["status"]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_stream_no_workers_yields_failed_event(self, storage, scheduler):
        """Test that missing workers produces a failed status event."""
        handlers = _make_handlers(storage, scheduler, manifest=None, workers=None)
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        status_events = [e for e in events if e["kind"] == "status-update"]
        assert status_events[0]["status"]["state"] == "working"
        assert status_events[-1]["status"]["state"] == "failed"
        assert "No agent worker available" in status_events[-1].get("error", "")

    @pytest.mark.asyncio
    async def test_stream_empty_workers_list_yields_failed_event(
        self, storage, scheduler
    ):
        """Test that an empty workers list is handled the same as None."""
        manifest = MockManifest()
        handlers = _make_handlers(storage, scheduler, manifest=manifest, workers=[])
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        status_events = [e for e in events if e["kind"] == "status-update"]
        assert status_events[-1]["status"]["state"] == "failed"
        assert "No agent worker available" in status_events[-1].get("error", "")

    @pytest.mark.asyncio
    async def test_stream_error_persists_error_message_to_storage(
        self, storage, scheduler
    ):
        """Test that error messages are persisted to task history."""
        manifest = MockManifest(
            agent_fn=MockAgent(response="test error", response_type="error")
        )
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        await _collect_sse_events(response)

        tasks = await storage.list_tasks()
        task = tasks[0]
        assert task["status"]["state"] == "failed"
        # Should have user message + error message
        assert len(task["history"]) >= 2
        error_msg = task["history"][-1]
        assert error_msg["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_stream_storage_error_in_error_path_does_not_crash(
        self, storage, scheduler
    ):
        """Test that a storage failure during error handling doesn't prevent
        the client from receiving the failure SSE event."""
        manifest = MockManifest(
            agent_fn=MockAgent(response="agent broke", response_type="error")
        )
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        # Poison the storage update to fail *after* the initial working transition
        original_update = storage.update_task
        call_count = 0

        async def failing_update(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # Let the first update (working) succeed, fail the error-path update
                raise RuntimeError("Storage is down")
            return await original_update(*args, **kwargs)

        storage.update_task = failing_update

        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        # Client still gets the failed status event even though storage broke
        status_events = [e for e in events if e["kind"] == "status-update"]
        assert any(e["status"]["state"] == "failed" for e in status_events)


# ---------------------------------------------------------------------------
# Payment Integration Tests
# ---------------------------------------------------------------------------


class TestStreamingPayment:
    """Test X402 payment context integration with streaming."""

    @pytest.mark.asyncio
    async def test_stream_forwards_payment_context(self, storage, scheduler):
        """Test that payment context is forwarded to settlement."""
        manifest = MockManifest(agent_fn=MockAgent(response="paid response"))
        worker = _make_worker(
            settle_result={"x402.status": "payment_completed"},
        )

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        payment_ctx = {
            "payment_payload": {"amount": 100},
            "payment_requirements": {"scheme": "exact"},
            "verify_response": {"success": True},
        }
        request = _make_stream_request(metadata={"_payment_context": payment_ctx})
        response = await handlers.stream_message(request)
        await _collect_sse_events(response)

        # Verify settlement was called via public API
        worker.settle_payment.assert_called_once_with(payment_ctx)

    @pytest.mark.asyncio
    async def test_stream_strips_payment_context_from_metadata(
        self, storage, scheduler
    ):
        """Test that _payment_context is removed from message metadata."""
        manifest = MockManifest(agent_fn=MockAgent(response="ok"))
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        payment_ctx = {
            "payment_payload": {},
            "payment_requirements": {},
            "verify_response": {},
        }
        request = _make_stream_request(metadata={"_payment_context": payment_ctx})

        # Access the message to check after
        msg = request["params"]["message"]
        response = await handlers.stream_message(request)
        await _collect_sse_events(response)

        # _payment_context should be stripped from message metadata
        assert "_payment_context" not in msg.get("metadata", {})


# ---------------------------------------------------------------------------
# Push Notification Tests
# ---------------------------------------------------------------------------


class TestStreamingPushNotifications:
    """Test push notification config registration for streaming."""

    @pytest.mark.asyncio
    async def test_stream_registers_push_config(self, storage, scheduler):
        """Test that push notification config is registered when provided."""
        manifest = MockManifest(agent_fn=MockAgent(response="notified"))
        worker = _make_worker()

        push_manager = MagicMock()
        push_manager.register_push_config = AsyncMock()

        handlers = _make_handlers(
            storage,
            scheduler,
            manifest=manifest,
            workers=[worker],
            push_manager=push_manager,
        )

        push_cfg = {"url": "https://example.com/webhook", "token": "secret"}
        request = _make_stream_request(
            configuration={
                "push_notification_config": push_cfg,
                "long_running": True,
            }
        )
        response = await handlers.stream_message(request)
        await _collect_sse_events(response)

        push_manager.register_push_config.assert_called_once()
        call_args = push_manager.register_push_config.call_args
        assert call_args[1]["persist"] is True


# ---------------------------------------------------------------------------
# Telemetry Tests
# ---------------------------------------------------------------------------


class TestStreamingTelemetry:
    """Test OpenTelemetry span and metrics on streaming."""

    @pytest.mark.asyncio
    async def test_stream_creates_telemetry_span(self, storage, scheduler):
        """Test that streaming creates and ends an OTel span."""
        manifest = MockManifest(agent_fn=MockAgent(response="traced"))
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        with patch("bindu.server.handlers.message_handlers._tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_span.return_value = mock_span

            response = await handlers.stream_message(_make_stream_request())
            await _collect_sse_events(response)

            # Span was started and ended
            mock_tracer.start_span.assert_called_once()
            mock_span.end.assert_called_once()

            # Span attributes were set on success
            mock_span.set_attribute.assert_any_call("bindu.stream.chunk_count", 1)
            mock_span.set_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_error_records_error_on_span(self, storage, scheduler):
        """Test that errors set ERROR status on the span."""
        manifest = MockManifest(
            agent_fn=MockAgent(response="fail", response_type="error")
        )
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        with patch("bindu.server.handlers.message_handlers._tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_span.return_value = mock_span

            response = await handlers.stream_message(_make_stream_request())
            await _collect_sse_events(response)

            # Span records error
            mock_span.set_attribute.assert_any_call("bindu.error_type", "ValueError")
            mock_span.end.assert_called_once()


# ---------------------------------------------------------------------------
# System Prompt Injection Tests
# ---------------------------------------------------------------------------


class TestStreamingSystemPrompt:
    """Test system prompt injection into the message history."""

    @pytest.mark.asyncio
    async def test_stream_injects_system_prompt_when_enabled(self, storage, scheduler):
        """Test that system prompt is prepended when manifest enables it."""
        manifest = MockManifest(agent_fn=MockAgent(response="with system"))
        manifest.enable_system_message = True

        # Capture what message_history the manifest.run() receives
        captured_history = []
        original_run = manifest.run

        def capturing_run(history):
            captured_history.extend(history)
            return original_run(history)

        manifest.run = capturing_run
        worker = _make_worker(history=[{"role": "user", "content": "hi"}])

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.agent.enable_structured_responses = True
            mock_settings.agent.structured_response_system_prompt = (
                "You are a helpful assistant."
            )

            response = await handlers.stream_message(_make_stream_request())
            await _collect_sse_events(response)

        # System prompt should be first in the history
        assert len(captured_history) >= 2
        assert captured_history[0]["role"] == "system"
        assert captured_history[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_stream_skips_system_prompt_when_disabled(self, storage, scheduler):
        """Test that system prompt is NOT injected when disabled."""
        manifest = MockManifest(agent_fn=MockAgent(response="no system"))
        manifest.enable_system_message = False

        captured_history = []
        original_run = manifest.run

        def capturing_run(history):
            captured_history.extend(history)
            return original_run(history)

        manifest.run = capturing_run
        worker = _make_worker(history=[{"role": "user", "content": "hi"}])

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )

        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.agent.enable_structured_responses = True
            mock_settings.agent.structured_response_system_prompt = "System"

            response = await handlers.stream_message(_make_stream_request())
            await _collect_sse_events(response)

        # No system message should be present
        assert not any(m.get("role") == "system" for m in captured_history)


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestStreamingEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_stream_empty_generator(self, storage, scheduler):
        """Test streaming with an empty generator (no chunks)."""
        manifest = MockManifest()

        def empty_gen(history):
            return
            yield  # Make it a generator that yields nothing

        manifest.run = empty_gen

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        # Should still complete (with empty response), no last_chunk marker
        # because no chunks were collected
        status_events = [e for e in events if e["kind"] == "status-update"]
        assert status_events[-1]["status"]["state"] == "completed"
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        assert len(artifact_events) == 0

    @pytest.mark.asyncio
    async def test_stream_none_chunks_are_skipped(self, storage, scheduler):
        """Test that None/falsy chunks from generator are skipped."""
        manifest = MockManifest()

        def sparse_gen(history):
            yield "hello"
            yield None
            yield ""
            yield "world"

        manifest.run = sparse_gen

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        content_events = [e for e in artifact_events if not e["last_chunk"]]
        texts = [e["artifact"]["parts"][0]["text"] for e in content_events]
        assert texts == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_stream_response_headers(self, storage, scheduler):
        """Test that streaming response has correct headers."""
        manifest = MockManifest(agent_fn=MockAgent(response="test"))
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())

        assert response.media_type == "text/event-stream"
        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("x-accel-buffering") == "no"
        assert response.headers.get("connection") == "keep-alive"

    @pytest.mark.asyncio
    async def test_stream_task_submitted_to_storage(self, storage, scheduler):
        """Test that the task is initially submitted to storage."""
        manifest = MockManifest(agent_fn=MockAgent(response="ok"))
        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())

        # Before consuming: task exists in storage as submitted
        tasks = await storage.list_tasks()
        assert len(tasks) == 1

        # After consuming: task is completed
        await _collect_sse_events(response)
        tasks = await storage.list_tasks()
        assert tasks[0]["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_stream_none_manifest_result(self, storage, scheduler):
        """Test streaming when manifest returns None."""
        manifest = MockManifest()
        manifest.run = lambda history: None

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        # No artifact events for None result
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        assert len(artifact_events) == 0

        # Should still complete
        status_events = [e for e in events if e["kind"] == "status-update"]
        assert status_events[-1]["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_stream_direct_return_no_last_chunk_marker(self, storage, scheduler):
        """Test that direct return path emits last_chunk=True on the single event,
        not a separate empty marker."""
        manifest = MockManifest()
        manifest.run = lambda history: "single"

        worker = _make_worker()

        handlers = _make_handlers(
            storage, scheduler, manifest=manifest, workers=[worker]
        )
        response = await handlers.stream_message(_make_stream_request())
        events = await _collect_sse_events(response)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        # Only one artifact event, with last_chunk=True
        assert len(artifact_events) == 1
        assert artifact_events[0]["last_chunk"] is True
        assert artifact_events[0]["artifact"]["parts"][0]["text"] == "single"
