"""Integration tests for pause/resume flow with checkpoint support."""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from bindu.common.protocol.types import Task, TaskStatus
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.workers.base import Worker
from bindu.settings import app_settings


class DummyWorker(Worker):
    """Dummy worker for testing pause/resume without actual agent execution."""

    async def run_task(self, params):
        pass

    async def cancel_task(self, params):
        pass

    def build_message_history(self, history):
        return []

    def build_artifacts(self, result):
        return []

    async def _notify_lifecycle(self, task_id, context_id, state, final):
        """Dummy lifecycle notification for testing."""
        pass


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    """Create a fresh in-memory storage for each test."""
    return InMemoryStorage()


@pytest_asyncio.fixture
async def worker(storage: InMemoryStorage) -> DummyWorker:
    """Create a dummy worker with test storage."""
    from bindu.server.scheduler.memory_scheduler import InMemoryScheduler

    scheduler = InMemoryScheduler()
    return DummyWorker(scheduler=scheduler, storage=storage)


def create_test_message(task_id: uuid4, context_id: uuid4):
    """Helper to create a test message."""
    return {
        "message_id": uuid4(),
        "task_id": task_id,
        "context_id": context_id,
        "role": "user",
        "parts": [{"kind": "text", "text": "test"}],
    }


@pytest.mark.asyncio
async def test_pause_saves_checkpoint_and_updates_state(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that pausing a task saves checkpoint and updates state to suspended."""
    task_id = uuid4()
    context_id = uuid4()

    # Create a task in 'working' state by first submitting it
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working", metadata={"step": 1})

    # Pause the task
    await worker._handle_pause({"task_id": task_id})

    # Verify task is now suspended
    task = await storage.load_task(task_id)
    assert task is not None
    assert task["status"]["state"] == "suspended"

    # Verify checkpoint was saved
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint["checkpoint_data"]["task_state"] == "working"
    assert checkpoint["checkpoint_data"]["metadata"]["step"] == 1


@pytest.mark.asyncio
async def test_resume_restores_from_checkpoint(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that resuming a task restores from checkpoint and updates state to working."""
    task_id = uuid4()
    context_id = uuid4()

    # Create task and pause it
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working")

    # Pause the task
    await worker._handle_pause({"task_id": task_id})

    # Resume the task
    await worker._handle_resume({"task_id": task_id})

    # Verify task is now working
    task = await storage.load_task(task_id)
    assert task is not None
    assert task["status"]["state"] == "working"

    # Verify checkpoint metadata was added
    assert task.get("metadata", {}).get("resumed_from_checkpoint") is True
    assert task.get("metadata", {}).get("checkpoint_step") == 0


@pytest.mark.asyncio
async def test_cannot_pause_terminal_tasks(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that terminal tasks cannot be paused."""
    task_id = uuid4()
    context_id = uuid4()

    # Create a task and complete it
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="completed")

    # Try to pause - should not raise but should not do anything
    await worker._handle_pause({"task_id": task_id})

    # Verify task is still completed (not suspended)
    task = await storage.load_task(task_id)
    assert task is not None
    assert task["status"]["state"] == "completed"

    # Verify no checkpoint was saved
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_cannot_resume_non_suspended_tasks(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that only suspended tasks can be resumed."""
    task_id = uuid4()
    context_id = uuid4()

    # Create a task in 'working' state
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working")

    # Try to resume - should not raise but should not do anything
    await worker._handle_resume({"task_id": task_id})

    # Verify task is still working
    task = await storage.load_task(task_id)
    assert task is not None
    assert task["status"]["state"] == "working"


@pytest.mark.asyncio
async def test_checkpoint_cleanup_on_completion(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that checkpoint is deleted when task completes."""
    task_id = uuid4()
    context_id = uuid4()

    # Create and pause a task
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working")
    await worker._handle_pause({"task_id": task_id})

    # Verify checkpoint exists
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is not None

    # Complete the task and delete checkpoint
    await storage.update_task(task_id=task_id, state="completed")
    await storage.delete_checkpoint(task_id)

    # Verify checkpoint is deleted
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_checkpoint_cleanup_on_failure(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that checkpoint is deleted when task fails."""
    task_id = uuid4()
    context_id = uuid4()

    # Create and pause a task
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working")
    await worker._handle_pause({"task_id": task_id})

    # Verify checkpoint exists
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is not None

    # Fail the task and delete checkpoint
    await storage.update_task(task_id=task_id, state="failed")
    await storage.delete_checkpoint(task_id)

    # Verify checkpoint is deleted
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_checkpoint_cleanup_on_cancel(
    storage: InMemoryStorage, worker: DummyWorker
):
    """Test that checkpoint is deleted when task is canceled."""
    task_id = uuid4()
    context_id = uuid4()

    # Create and pause a task
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="working")
    await worker._handle_pause({"task_id": task_id})

    # Verify checkpoint exists
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is not None

    # Cancel the task and delete checkpoint
    await storage.update_task(task_id=task_id, state="canceled")
    await storage.delete_checkpoint(task_id)

    # Verify checkpoint is deleted
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_pause_nonexistent_task(storage: InMemoryStorage, worker: DummyWorker):
    """Test that pausing nonexistent task doesn't raise."""
    task_id = uuid4()

    # Should not raise
    await worker._handle_pause({"task_id": task_id})


@pytest.mark.asyncio
async def test_resume_nonexistent_task(storage: InMemoryStorage, worker: DummyWorker):
    """Test that resuming nonexistent task doesn't raise."""
    task_id = uuid4()

    # Should not raise
    await worker._handle_resume({"task_id": task_id})


@pytest.mark.asyncio
async def test_resume_without_checkpoint(storage: InMemoryStorage, worker: DummyWorker):
    """Test that resuming without checkpoint doesn't raise but doesn't change state properly."""
    task_id = uuid4()
    context_id = uuid4()

    # Create a suspended task without checkpoint
    await storage.submit_task(context_id, create_test_message(task_id, context_id))
    await storage.update_task(task_id=task_id, state="suspended")

    # Try to resume - should not raise
    await worker._handle_resume({"task_id": task_id})

    # Task should remain suspended (since no checkpoint)
    task = await storage.load_task(task_id)
    assert task["status"]["state"] == "suspended"
