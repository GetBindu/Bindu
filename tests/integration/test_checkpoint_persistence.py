"""Integration tests for checkpoint persistence."""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from bindu.server.storage.memory_storage import InMemoryStorage


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    """Create a fresh in-memory storage for each test."""
    return InMemoryStorage()


@pytest.mark.asyncio
async def test_checkpoint_save_and_retrieve(storage: InMemoryStorage):
    """Test basic checkpoint save and retrieve."""
    task_id = uuid4()
    checkpoint_data = {"step": 1, "progress": 50, "data": {"key": "value"}}

    # Save checkpoint
    await storage.save_checkpoint(
        task_id=task_id,
        checkpoint_data=checkpoint_data,
        step_number=1,
        step_label="step-1",
    )

    # Retrieve checkpoint
    checkpoint = await storage.get_checkpoint(task_id)

    assert checkpoint is not None
    assert checkpoint["checkpoint_data"] == checkpoint_data
    assert checkpoint["step_number"] == 1
    assert checkpoint["step_label"] == "step-1"


@pytest.mark.asyncio
async def test_checkpoint_with_step_info(storage: InMemoryStorage):
    """Test checkpoint stores step information correctly."""
    task_id = uuid4()

    # Save checkpoint with step info
    await storage.save_checkpoint(
        task_id=task_id,
        checkpoint_data={"message": "test"},
        step_number=5,
        step_label="processing",
    )

    checkpoint = await storage.get_checkpoint(task_id)

    assert checkpoint["step_number"] == 5
    assert checkpoint["step_label"] == "processing"


@pytest.mark.asyncio
async def test_multiple_checkpoints_returns_latest(storage: InMemoryStorage):
    """Test that get_checkpoint returns the most recent checkpoint."""
    task_id = uuid4()

    # Save multiple checkpoints
    await storage.save_checkpoint(
        task_id=task_id, checkpoint_data={"step": 1}, step_number=1
    )
    await storage.save_checkpoint(
        task_id=task_id, checkpoint_data={"step": 2}, step_number=2
    )
    await storage.save_checkpoint(
        task_id=task_id, checkpoint_data={"step": 3}, step_number=3
    )

    # Get should return the latest
    checkpoint = await storage.get_checkpoint(task_id)

    assert checkpoint["checkpoint_data"]["step"] == 3
    assert checkpoint["step_number"] == 3


@pytest.mark.asyncio
async def test_delete_checkpoint(storage: InMemoryStorage):
    """Test checkpoint deletion."""
    task_id = uuid4()

    # Save checkpoint
    await storage.save_checkpoint(task_id=task_id, checkpoint_data={"test": True})

    # Verify exists
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is not None

    # Delete
    await storage.delete_checkpoint(task_id)

    # Verify deleted
    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_delete_nonexistent_checkpoint(storage: InMemoryStorage):
    """Test deleting nonexistent checkpoint doesn't raise."""
    task_id = uuid4()

    # Should not raise
    await storage.delete_checkpoint(task_id)


@pytest.mark.asyncio
async def test_get_nonexistent_checkpoint(storage: InMemoryStorage):
    """Test getting nonexistent checkpoint returns None."""
    task_id = uuid4()

    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint is None


@pytest.mark.asyncio
async def test_checkpoint_stores_task_id(storage: InMemoryStorage):
    """Test that checkpoint correctly stores task_id for reference."""
    task_id = uuid4()

    await storage.save_checkpoint(task_id=task_id, checkpoint_data={"test": True})

    checkpoints = await storage.list_checkpoints(task_id=task_id)

    assert len(checkpoints) == 1
    assert checkpoints[0]["task_id"] == task_id


@pytest.mark.asyncio
async def test_list_checkpoints_with_limit(storage: InMemoryStorage):
    """Test listing checkpoints with limit."""
    task_id = uuid4()

    # Create multiple checkpoints
    for i in range(10):
        await storage.save_checkpoint(
            task_id=task_id, checkpoint_data={"step": i}, step_number=i
        )

    # List with limit
    checkpoints = await storage.list_checkpoints(limit=5)

    # Should return only 5 (most recent)
    assert len(checkpoints) == 5


@pytest.mark.asyncio
async def test_list_checkpoints_by_task_id(storage: InMemoryStorage):
    """Test listing checkpoints filtered by task_id."""
    task_id_1 = uuid4()
    task_id_2 = uuid4()

    # Create checkpoints for two tasks
    await storage.save_checkpoint(task_id=task_id_1, checkpoint_data={"task": 1})
    await storage.save_checkpoint(task_id=task_id_2, checkpoint_data={"task": 2})
    await storage.save_checkpoint(
        task_id=task_id_1, checkpoint_data={"task": 1, "step": 2}
    )

    # List checkpoints for task_id_1 only
    checkpoints = await storage.list_checkpoints(task_id=task_id_1)

    assert len(checkpoints) == 2
    for cp in checkpoints:
        assert cp["task_id"] == task_id_1


@pytest.mark.asyncio
async def test_checkpoint_data_types(storage: InMemoryStorage):
    """Test checkpoint handles various data types."""
    task_id = uuid4()

    complex_data = {
        "string": "test",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "nested": {"a": {"b": {"c": 1}}},
    }

    await storage.save_checkpoint(task_id=task_id, checkpoint_data=complex_data)

    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint["checkpoint_data"] == complex_data


@pytest.mark.asyncio
async def test_checkpoint_empty_data(storage: InMemoryStorage):
    """Test checkpoint with empty data."""
    task_id = uuid4()

    await storage.save_checkpoint(task_id=task_id, checkpoint_data={})

    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint["checkpoint_data"] == {}


@pytest.mark.asyncio
async def test_checkpoint_with_uuid_objects(storage: InMemoryStorage):
    """Test checkpoint correctly stores UUID objects."""
    task_id = uuid4()
    nested_uuid = uuid4()

    await storage.save_checkpoint(
        task_id=task_id,
        checkpoint_data={"nested_uuid": str(nested_uuid), "uuid": str(task_id)},
    )

    checkpoint = await storage.get_checkpoint(task_id)
    assert checkpoint["checkpoint_data"]["uuid"] == str(task_id)
    assert checkpoint["checkpoint_data"]["nested_uuid"] == str(nested_uuid)
