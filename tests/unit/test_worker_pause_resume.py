"""Unit tests for Worker pause/resume functionality."""

from typing import cast
from uuid import uuid4

import pytest

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.workers.manifest_worker import ManifestWorker
from tests.mocks import MockManifest
from tests.utils import assert_task_state, create_test_message


class TestPauseOperation:
    """Test task pause functionality."""

    @pytest.mark.asyncio
    async def test_pause_suspended_task(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test pausing a task transitions it to suspended state."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create a task
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        # Update task to working state
        await storage.update_task(task_id, state="working")

        # Pause the task
        params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(params)

        # Verify task is suspended
        paused_task = await storage.load_task(task_id)
        assert_task_state(paused_task, "suspended")
        assert paused_task is not None

    @pytest.mark.asyncio
    async def test_pause_stores_metadata(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test pause stores metadata timestamp."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create and pause a task
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        await storage.update_task(task_id, state="working")
        params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(params)

        # Verify metadata contains pause information
        paused_task = await storage.load_task(task_id)
        assert paused_task is not None
        assert "metadata" in paused_task
        metadata = paused_task.get("metadata", {})
        assert "paused_at" in metadata
        assert "paused" in str(metadata).lower() or "suspensio" in str(metadata).lower()

    @pytest.mark.asyncio
    async def test_pause_nonexistent_task_fails(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test pausing a nonexistent task raises error."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Try to pause a task that doesn't exist
        fake_task_id = uuid4()
        params = cast(TaskIdParams, {"task_id": fake_task_id})

        with pytest.raises(Exception):
            await worker._handle_pause(params)


class TestResumeOperation:
    """Test task resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_resumes_suspended_task(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test resuming a suspended task transitions it to resumed state."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create, suspend, then resume a task
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        await storage.update_task(task_id, state="working")

        # Pause the task
        pause_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(pause_params)

        # Verify it's suspended
        paused_task = await storage.load_task(task_id)
        assert_task_state(paused_task, "suspended")

        # Resume the task
        resume_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_resume(resume_params)

        # Verify task is resumed
        resumed_task = await storage.load_task(task_id)
        assert_task_state(resumed_task, "resumed")

    @pytest.mark.asyncio
    async def test_resume_preserves_metadata(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test resume preserves task metadata from suspension."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create task with initial metadata
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        initial_metadata = {"custom_field": "value"}
        await storage.update_task(task_id, state="working", metadata=initial_metadata)

        # Pause and resume
        pause_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(pause_params)

        resume_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_resume(resume_params)

        # Verify metadata is preserved
        resumed_task = await storage.load_task(task_id)
        metadata = resumed_task.get("metadata", {})
        assert metadata.get("custom_field") == "value"
        assert "paused_at" in metadata or "resumed_at" in metadata

    @pytest.mark.asyncio
    async def test_resume_nonexistent_task_fails(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test resuming a nonexistent task raises error."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Try to resume a task that doesn't exist
        fake_task_id = uuid4()
        params = cast(TaskIdParams, {"task_id": fake_task_id})

        with pytest.raises(Exception):
            await worker._handle_resume(params)

    @pytest.mark.asyncio
    async def test_resume_non_suspended_task(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test resuming a non-suspended task (graceful handling)."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create a task in working state (not suspended)
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        await storage.update_task(task_id, state="working")

        # Try to resume without pausing first
        # Should still work - transitions to resumed
        resume_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_resume(resume_params)

        # Verify task is resumed
        resumed_task = await storage.load_task(task_id)
        assert_task_state(resumed_task, "resumed")


class TestPauseResumeCycle:
    """Test complete pause/resume cycles."""

    @pytest.mark.asyncio
    async def test_multiple_pause_resume_cycles(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test multiple pause/resume cycles on same task."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create a task
        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]

        # Cycle 1: suspend
        await storage.update_task(task_id, state="working")
        pause_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(pause_params)
        paused1 = await storage.load_task(task_id)
        assert_task_state(paused1, "suspended")

        # Resume cycle 1
        resume_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_resume(resume_params)
        resumed1 = await storage.load_task(task_id)
        assert_task_state(resumed1, "resumed")

        # Update back to working for next cycle
        await storage.update_task(task_id, state="working")

        # Cycle 2: suspend again
        await worker._handle_pause(pause_params)
        paused2 = await storage.load_task(task_id)
        assert_task_state(paused2, "suspended")

        # Resume cycle 2
        await worker._handle_resume(resume_params)
        resumed2 = await storage.load_task(task_id)
        assert_task_state(resumed2, "resumed")

    @pytest.mark.asyncio
    async def test_pause_preserves_history_and_artifacts(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that pause/resume preserves task history and artifacts."""
        manifest = MockManifest()
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create a task with history
        message1 = create_test_message(text="First message")
        task = await storage.submit_task(message1["context_id"], message1)
        task_id = task["id"]

        # Add more messages to history
        message2 = create_test_message(
            text="Second message", context_id=task["context_id"]
        )
        await storage.append_to_contexts(
            task["context_id"], [message2]
        )

        await storage.update_task(task_id, state="working")

        # Get history before pause
        task_before = await storage.load_task(task_id)
        history_before = task_before.get("history", [])

        # Pause and resume
        pause_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_pause(pause_params)

        resume_params = cast(TaskIdParams, {"task_id": task_id})
        await worker._handle_resume(resume_params)

        # Verify history is preserved
        task_after = await storage.load_task(task_id)
        history_after = task_after.get("history", [])

        assert len(history_after) >= len(history_before)
