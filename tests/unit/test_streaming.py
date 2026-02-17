"""Comprehensive tests for Streaming SSE (Issue #143).

Tests cover:
- ManifestWorker.stream_task() with sync generators, async generators, and direct returns
- Storage.append_artifact_chunk() for InMemoryStorage
- MessageHandlers.stream_message() handler delegation
- SSE event types (TaskStatusUpdateEvent, TaskArtifactUpdateEvent)
- Error handling during streaming
- Payment context forwarding in streaming
- Settings and routing for message/stream
"""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskStatusUpdateEvent,
    TextPart,
)
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.workers.manifest_worker import ManifestWorker
from tests.mocks import MockAgent, MockDIDExtension, MockManifest
from tests.utils import create_test_message


# ---------------------------------------------------------------------------
# Helper: Streaming mock agents
# ---------------------------------------------------------------------------


class StreamingMockAgent:
    """Mock agent that returns a sync generator (simulating streaming LLM output)."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.call_count = 0

    def __call__(self, message: str) -> str:
        self.call_count += 1
        # Return all chunks joined — manifest.run() will yield them
        return "\n".join(self.chunks)


class StreamingMockManifest(MockManifest):
    """Mock manifest that yields chunks via a sync generator."""

    def __init__(self, chunks: list[str], **kwargs):
        super().__init__(**kwargs)
        self.chunks = chunks

    def run(self, message_history: list):
        """Yield each chunk as a separate generator value."""
        for chunk in self.chunks:
            yield chunk


class AsyncStreamingMockManifest(MockManifest):
    """Mock manifest that yields chunks via an async generator."""

    def __init__(self, chunks: list[str], **kwargs):
        super().__init__(**kwargs)
        self.chunks = chunks

    def run(self, message_history: list):
        """Return an async generator of chunks."""
        return self._async_gen()

    async def _async_gen(self):
        for chunk in self.chunks:
            yield chunk


class DirectReturnMockManifest(MockManifest):
    """Mock manifest that returns a direct value (not a generator)."""

    def __init__(self, result: str, **kwargs):
        super().__init__(**kwargs)
        self._result = result

    def run(self, message_history: list):
        """Return a direct value, not a generator."""
        return self._result


class ErrorMockManifest(MockManifest):
    """Mock manifest that raises an error during execution."""

    def __init__(self, error_message: str = "Agent execution failed", **kwargs):
        super().__init__(**kwargs)
        self._error_message = error_message

    def run(self, message_history: list):
        raise RuntimeError(self._error_message)


class ErrorMidStreamManifest(MockManifest):
    """Mock manifest that errors midway through streaming."""

    def __init__(self, chunks_before_error: list[str], error_message: str, **kwargs):
        super().__init__(**kwargs)
        self.chunks_before_error = chunks_before_error
        self._error_message = error_message

    def run(self, message_history: list):
        for chunk in self.chunks_before_error:
            yield chunk
        raise RuntimeError(self._error_message)


# ---------------------------------------------------------------------------
# Helper: Collect events from async generator
# ---------------------------------------------------------------------------


async def collect_stream_events(
    worker: ManifestWorker, params: TaskSendParams
) -> list[dict[str, Any]]:
    """Collect all events from stream_task() into a list."""
    events = []
    async for event in worker.stream_task(params):
        events.append(dict(event))
    return events


# ===========================================================================
# Test Suite 1: ManifestWorker.stream_task() — Sync Generator
# ===========================================================================


class TestStreamTaskSyncGenerator:
    """Test streaming with sync generator manifests."""

    @pytest.mark.asyncio
    async def test_stream_yields_working_status_first(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """First event should be a working status update."""
        manifest = StreamingMockManifest(chunks=["Hello", "World"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Stream test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        assert len(events) > 0
        first = events[0]
        assert first["kind"] == "status-update"
        assert first["status"]["state"] == "working"
        assert first["final"] is False

    @pytest.mark.asyncio
    async def test_stream_yields_artifact_chunks(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Each chunk should yield an artifact-update event with append=True."""
        chunks = ["Hello", " ", "World"]
        manifest = StreamingMockManifest(chunks=chunks)
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Stream test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        # Should have chunk events + final artifact event(s)
        assert len(artifact_events) >= len(chunks)

        # First N artifact events should have append=True, last_chunk=False
        for i, chunk in enumerate(chunks):
            ae = artifact_events[i]
            assert ae["append"] is True
            assert ae.get("last_chunk") is not True
            assert ae["artifact"]["parts"][0]["text"] == chunk

    @pytest.mark.asyncio
    async def test_stream_uses_stable_artifact_id(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """All chunk events should use the same artifact_id."""
        chunks = ["A", "B", "C"]
        manifest = StreamingMockManifest(chunks=chunks)
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        # All chunk artifacts (non-final) should share the same artifact_id
        chunk_ids = {
            ae["artifact"]["artifact_id"]
            for ae in artifact_events
            if ae.get("last_chunk") is not True
        }
        assert len(chunk_ids) == 1, f"Expected 1 unique artifact_id, got {chunk_ids}"

    @pytest.mark.asyncio
    async def test_stream_yields_final_artifact_with_last_chunk(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Final artifact event should have last_chunk=True."""
        manifest = StreamingMockManifest(chunks=["Hello", "World"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        final_artifacts = [
            e for e in events if e["kind"] == "artifact-update" and e.get("last_chunk")
        ]
        assert len(final_artifacts) >= 1, "Should have at least one final artifact chunk"

    @pytest.mark.asyncio
    async def test_stream_yields_completed_status_last(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Last event should be a completed status update with final=True."""
        manifest = StreamingMockManifest(chunks=["Hello"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        last = events[-1]
        assert last["kind"] == "status-update"
        assert last["status"]["state"] == "completed"
        assert last["final"] is True

    @pytest.mark.asyncio
    async def test_stream_updates_storage_on_completion(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Storage should reflect completed state with artifacts after streaming."""
        manifest = StreamingMockManifest(chunks=["Result text"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        await collect_stream_events(worker, params)

        # Verify storage was updated
        updated_task = await storage.load_task(task["id"])
        assert updated_task is not None
        assert updated_task["status"]["state"] == "completed"
        assert len(updated_task.get("artifacts", [])) > 0


# ===========================================================================
# Test Suite 2: ManifestWorker.stream_task() — Async Generator
# ===========================================================================


class TestStreamTaskAsyncGenerator:
    """Test streaming with async generator manifests."""

    @pytest.mark.asyncio
    async def test_async_stream_yields_chunks(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Async generator chunks should produce artifact-update events."""
        chunks = ["Async", "chunk", "output"]
        manifest = AsyncStreamingMockManifest(chunks=chunks)
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Async test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        chunk_events = [e for e in artifact_events if e.get("last_chunk") is not True]
        assert len(chunk_events) == len(chunks)

        for i, chunk in enumerate(chunks):
            assert chunk_events[i]["artifact"]["parts"][0]["text"] == chunk

    @pytest.mark.asyncio
    async def test_async_stream_full_lifecycle(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Full streaming lifecycle: working → chunks → final artifact → completed."""
        chunks = ["Part1", "Part2"]
        manifest = AsyncStreamingMockManifest(chunks=chunks)
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Lifecycle test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        # First: working status
        assert events[0]["kind"] == "status-update"
        assert events[0]["status"]["state"] == "working"

        # Middle: artifact chunks
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        assert len(artifact_events) >= 2

        # Last: completed status
        assert events[-1]["kind"] == "status-update"
        assert events[-1]["status"]["state"] == "completed"


# ===========================================================================
# Test Suite 3: ManifestWorker.stream_task() — Direct Return
# ===========================================================================


class TestStreamTaskDirectReturn:
    """Test streaming when manifest returns a direct value (not generator)."""

    @pytest.mark.asyncio
    async def test_direct_return_yields_final_artifact(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Direct return should yield a final artifact with the result."""
        manifest = DirectReturnMockManifest(result="Direct result")
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Direct test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        # Should have: working status + final artifact(s) + completed status
        status_events = [e for e in events if e["kind"] == "status-update"]
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]

        assert len(status_events) == 2  # working + completed
        assert len(artifact_events) >= 1  # at least one final artifact

        # Final artifact should have last_chunk=True
        assert artifact_events[-1].get("last_chunk") is True

    @pytest.mark.asyncio
    async def test_direct_return_completes_task(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Direct return should complete the task in storage."""
        manifest = DirectReturnMockManifest(result="Done")
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        await collect_stream_events(worker, params)

        updated = await storage.load_task(task["id"])
        assert updated["status"]["state"] == "completed"


# ===========================================================================
# Test Suite 4: Error Handling
# ===========================================================================


class TestStreamTaskErrorHandling:
    """Test error handling during streaming."""

    @pytest.mark.asyncio
    async def test_error_yields_failed_status(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Manifest error should yield a failed status event."""
        manifest = ErrorMockManifest(error_message="Boom!")
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Error test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        # Should have working status followed by failed status
        failed_events = [
            e
            for e in events
            if e["kind"] == "status-update" and e["status"]["state"] == "failed"
        ]
        assert len(failed_events) == 1
        assert failed_events[0]["final"] is True

    @pytest.mark.asyncio
    async def test_error_updates_storage_to_failed(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Manifest error should mark task as failed in storage."""
        manifest = ErrorMockManifest(error_message="Agent crash")
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Error test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        await collect_stream_events(worker, params)

        updated = await storage.load_task(task["id"])
        assert updated["status"]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_error_includes_message_in_metadata(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Failed status event should include error message."""
        manifest = ErrorMockManifest(error_message="Specific failure reason")
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Error test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        failed = [
            e
            for e in events
            if e["kind"] == "status-update" and e["status"]["state"] == "failed"
        ][0]
        assert "Specific failure reason" in failed.get("metadata", {}).get("error", "")

    @pytest.mark.asyncio
    async def test_mid_stream_error_yields_partial_chunks_then_failure(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Error mid-stream should yield partial chunks then a failure event."""
        manifest = ErrorMidStreamManifest(
            chunks_before_error=["chunk1", "chunk2"],
            error_message="Mid-stream failure",
        )
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Mid-stream error")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        # Should have: working status + some chunks + failed status
        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        failed_events = [
            e
            for e in events
            if e["kind"] == "status-update" and e["status"]["state"] == "failed"
        ]

        assert len(artifact_events) >= 2  # At least the chunks before error
        assert len(failed_events) == 1

    @pytest.mark.asyncio
    async def test_task_not_found_raises(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """stream_task() with non-existent task should raise ValueError."""
        manifest = StreamingMockManifest(chunks=["test"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        params = cast(
            TaskSendParams,
            {"task_id": uuid4(), "context_id": uuid4(), "message": create_test_message()},
        )

        with pytest.raises(ValueError, match="not found"):
            await collect_stream_events(worker, params)


# ===========================================================================
# Test Suite 5: Storage — append_artifact_chunk()
# ===========================================================================


class TestAppendArtifactChunk:
    """Test InMemoryStorage.append_artifact_chunk()."""

    @pytest.mark.asyncio
    async def test_append_creates_new_artifact(self, storage: InMemoryStorage):
        """Appending to a task with no artifacts creates one."""
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        artifact_id = uuid4()
        chunk = Artifact(
            artifact_id=artifact_id,
            name="test",
            parts=[TextPart(kind="text", text="chunk1")],
            append=True,
        )

        await storage.append_artifact_chunk(task["id"], chunk)

        updated = await storage.load_task(task["id"])
        assert len(updated.get("artifacts", [])) == 1
        assert updated["artifacts"][0]["artifact_id"] == artifact_id

    @pytest.mark.asyncio
    async def test_append_extends_existing_artifact(self, storage: InMemoryStorage):
        """Appending with same artifact_id extends parts."""
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        artifact_id = uuid4()

        chunk1 = Artifact(
            artifact_id=artifact_id,
            name="test",
            parts=[TextPart(kind="text", text="chunk1")],
            append=True,
        )
        chunk2 = Artifact(
            artifact_id=artifact_id,
            name="test",
            parts=[TextPart(kind="text", text="chunk2")],
            append=True,
        )

        await storage.append_artifact_chunk(task["id"], chunk1)
        await storage.append_artifact_chunk(task["id"], chunk2)

        updated = await storage.load_task(task["id"])
        # Should remain as one artifact with 2 parts
        assert len(updated["artifacts"]) == 1
        assert len(updated["artifacts"][0]["parts"]) == 2
        assert updated["artifacts"][0]["parts"][0]["text"] == "chunk1"
        assert updated["artifacts"][0]["parts"][1]["text"] == "chunk2"

    @pytest.mark.asyncio
    async def test_append_different_artifact_ids(self, storage: InMemoryStorage):
        """Different artifact_ids create separate artifacts."""
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        chunk1 = Artifact(
            artifact_id=uuid4(),
            name="artifact_a",
            parts=[TextPart(kind="text", text="A")],
        )
        chunk2 = Artifact(
            artifact_id=uuid4(),
            name="artifact_b",
            parts=[TextPart(kind="text", text="B")],
        )

        await storage.append_artifact_chunk(task["id"], chunk1)
        await storage.append_artifact_chunk(task["id"], chunk2)

        updated = await storage.load_task(task["id"])
        assert len(updated["artifacts"]) == 2

    @pytest.mark.asyncio
    async def test_append_task_not_found_raises(self, storage: InMemoryStorage):
        """Appending to non-existent task raises KeyError."""
        chunk = Artifact(
            artifact_id=uuid4(),
            parts=[TextPart(kind="text", text="test")],
        )

        with pytest.raises(KeyError):
            await storage.append_artifact_chunk(uuid4(), chunk)

    @pytest.mark.asyncio
    async def test_append_invalid_task_id_type_raises(self, storage: InMemoryStorage):
        """Non-UUID task_id raises TypeError."""
        chunk = Artifact(
            artifact_id=uuid4(),
            parts=[TextPart(kind="text", text="test")],
        )

        with pytest.raises(TypeError):
            await storage.append_artifact_chunk("not-a-uuid", chunk)  # type: ignore


# ===========================================================================
# Test Suite 6: SSE Event Type Compliance
# ===========================================================================


class TestSSEEventTypes:
    """Test that streamed events conform to A2A protocol types."""

    @pytest.mark.asyncio
    async def test_status_events_have_required_fields(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """TaskStatusUpdateEvent must have task_id, context_id, kind, status, final."""
        manifest = StreamingMockManifest(chunks=["test"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Type check")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        status_events = [e for e in events if e["kind"] == "status-update"]
        for se in status_events:
            assert "task_id" in se
            assert "context_id" in se
            assert "kind" in se
            assert se["kind"] == "status-update"
            assert "status" in se
            assert "state" in se["status"]
            assert "final" in se

    @pytest.mark.asyncio
    async def test_artifact_events_have_required_fields(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """TaskArtifactUpdateEvent must have task_id, context_id, kind, artifact."""
        manifest = StreamingMockManifest(chunks=["test"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Type check")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        artifact_events = [e for e in events if e["kind"] == "artifact-update"]
        for ae in artifact_events:
            assert "task_id" in ae
            assert "context_id" in ae
            assert "kind" in ae
            assert ae["kind"] == "artifact-update"
            assert "artifact" in ae
            assert "artifact_id" in ae["artifact"]

    @pytest.mark.asyncio
    async def test_events_are_json_serializable(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """All streamed events must be JSON-serializable for SSE transport."""
        manifest = StreamingMockManifest(chunks=["Hello", "World"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="JSON test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        for event in events:
            # Should not raise — all events must be serializable
            serialized = json.dumps(event, default=str)
            assert isinstance(serialized, str)


# ===========================================================================
# Test Suite 7: Lifecycle Notifications
# ===========================================================================


class TestStreamingLifecycleNotifications:
    """Test that push notifications fire during streaming."""

    @pytest.mark.asyncio
    async def test_lifecycle_notifier_called_on_working(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Lifecycle notifier should be called when transitioning to working."""
        notifications: list[tuple] = []

        async def mock_notifier(task_id, context_id, state, final):
            notifications.append((task_id, context_id, state, final))

        manifest = StreamingMockManifest(chunks=["test"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
            lifecycle_notifier=mock_notifier,
        )

        message = create_test_message(text="Notification test")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        await collect_stream_events(worker, params)

        # Should have working (non-final) and completed (final)
        states = [n[2] for n in notifications]
        assert "working" in states
        assert "completed" in states

        # Working should be non-final
        working_notif = [n for n in notifications if n[2] == "working"][0]
        assert working_notif[3] is False  # final=False

        # Completed should be final
        completed_notif = [n for n in notifications if n[2] == "completed"][0]
        assert completed_notif[3] is True  # final=True


# ===========================================================================
# Test Suite 8: Settings and Routing
# ===========================================================================


class TestStreamingSettings:
    """Test settings configuration for streaming."""

    def test_message_stream_in_method_handlers(self):
        """message/stream should be mapped in method_handlers."""
        from bindu.settings import app_settings

        handlers = app_settings.agent.method_handlers
        assert "message/stream" in handlers
        assert handlers["message/stream"] == "stream_message"

    def test_message_stream_in_protected_methods(self):
        """message/stream should be in x402 protected methods."""
        from bindu.settings import app_settings

        assert "message/stream" in app_settings.x402.protected_methods

    def test_message_stream_in_permissions(self):
        """message/stream should have agent:write permission."""
        from bindu.settings import app_settings

        assert "message/stream" in app_settings.auth.permissions
        assert "agent:write" in app_settings.auth.permissions["message/stream"]


# ===========================================================================
# Test Suite 9: Message Handler Integration
# ===========================================================================


class TestStreamMessageHandler:
    """Test MessageHandlers.stream_message() integration."""

    @pytest.mark.asyncio
    async def test_stream_message_returns_streaming_response(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """stream_message() should return a StreamingResponse."""
        from starlette.responses import StreamingResponse

        from bindu.server.handlers.message_handlers import MessageHandlers

        manifest = StreamingMockManifest(chunks=["Hello"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        def context_id_parser(cid):
            from uuid import UUID as _UUID

            if isinstance(cid, str):
                return _UUID(cid)
            return cid if cid else uuid4()

        handler = MessageHandlers(
            scheduler=scheduler,
            storage=storage,
            manifest=manifest,
            workers=[worker],
            context_id_parser=context_id_parser,
        )

        msg_id = uuid4()
        ctx_id = uuid4()
        task_id = uuid4()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Hello"}],
                    "message_id": str(msg_id),
                    "task_id": str(task_id),
                    "context_id": str(ctx_id),
                }
            },
        }

        result = await handler.stream_message(request)
        assert isinstance(result, StreamingResponse)
        assert result.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_stream_message_creates_task_in_storage(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """stream_message() should create a task before streaming."""
        from bindu.server.handlers.message_handlers import MessageHandlers

        manifest = StreamingMockManifest(chunks=["Hello"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        def context_id_parser(cid):
            from uuid import UUID as _UUID

            if isinstance(cid, str):
                return _UUID(cid)
            return cid if cid else uuid4()

        handler = MessageHandlers(
            scheduler=scheduler,
            storage=storage,
            manifest=manifest,
            workers=[worker],
            context_id_parser=context_id_parser,
        )

        context_id = uuid4()
        task_id = uuid4()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Hello"}],
                    "message_id": str(uuid4()),
                    "task_id": str(task_id),
                    "context_id": str(context_id),
                }
            },
        }

        await handler.stream_message(request)

        # Task should exist in storage
        tasks = await storage.list_tasks_by_context(context_id)
        assert len(tasks) == 1
        assert tasks[0]["status"]["state"] == "submitted"


# ===========================================================================
# Test Suite 10: Empty and Edge Cases
# ===========================================================================


class TestStreamingEdgeCases:
    """Test edge cases in streaming."""

    @pytest.mark.asyncio
    async def test_empty_chunks_are_skipped(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Empty/falsy chunks should not produce artifact events."""

        class EmptyChunkManifest(MockManifest):
            def run(self, message_history):
                yield ""
                yield None
                yield "real_chunk"
                yield ""

        manifest = EmptyChunkManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Edge case")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        chunk_events = [
            e
            for e in events
            if e["kind"] == "artifact-update" and e.get("last_chunk") is not True
        ]
        # Only "real_chunk" should be yielded
        assert len(chunk_events) == 1
        assert chunk_events[0]["artifact"]["parts"][0]["text"] == "real_chunk"

    @pytest.mark.asyncio
    async def test_single_chunk_stream(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Single chunk streaming should still produce proper lifecycle."""
        manifest = StreamingMockManifest(chunks=["only_chunk"])
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Single chunk")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        # Should have: working + chunk artifact + final artifact + completed
        assert events[0]["kind"] == "status-update"
        assert events[0]["status"]["state"] == "working"
        assert events[-1]["kind"] == "status-update"
        assert events[-1]["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_large_number_of_chunks(
        self, storage: InMemoryStorage, scheduler: InMemoryScheduler
    ):
        """Handle many chunks without issue."""
        chunks = [f"chunk_{i}" for i in range(100)]
        manifest = StreamingMockManifest(chunks=chunks)
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Many chunks")
        task = await storage.submit_task(message["context_id"], message)
        params = cast(
            TaskSendParams,
            {"task_id": task["id"], "context_id": task["context_id"], "message": message},
        )

        events = await collect_stream_events(worker, params)

        chunk_events = [
            e
            for e in events
            if e["kind"] == "artifact-update" and e.get("last_chunk") is not True
        ]
        assert len(chunk_events) == 100

        # Task should still complete
        updated = await storage.load_task(task["id"])
        assert updated["status"]["state"] == "completed"
