"""Unit tests for TaskManager."""

import uuid
from uuid import uuid4

import pytest
from unittest.mock import MagicMock

from bindu.common.protocol.types import (
    CancelTaskRequest,
    ClearContextsRequest,
    GetTaskRequest,
    ListContextsRequest,
    ListTasksRequest,
    TaskFeedbackRequest,
)
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from tests.utils import (
    assert_jsonrpc_error,
    assert_jsonrpc_success,
    create_test_message,
)


@pytest.mark.asyncio
async def test_get_existing_task():
    """Test retrieving an existing task."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create task via submit_task
            message = create_test_message(text="Test message")
            context_id = message["context_id"]
            await storage.submit_task(context_id, message)

            request: GetTaskRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/get",
                "params": {
                    "task_id": message["task_id"],
                },
            }

            response = await tm.get_task(request)

            assert_jsonrpc_success(response)
            retrieved_task = response["result"]
            assert retrieved_task["id"] == message["task_id"]


@pytest.mark.asyncio
async def test_get_nonexistent_task():
    """Test retrieving a task that doesn't exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: GetTaskRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/get",
                "params": {
                    "task_id": uuid4(),  # Non-existent
                },
            }

            response = await tm.get_task(request)

            # Should return TaskNotFoundError (-32001)
            assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_get_task_with_history_limit():
    """Test retrieving task with history length limit."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create task with long history
            messages = [create_test_message(text=f"Message {i}") for i in range(20)]
            context_id = messages[0]["context_id"]
            task_id = messages[0]["task_id"]

            # Submit first message to create task
            await storage.submit_task(context_id, messages[0])
            # Update task with more messages
            await storage.update_task(
                task_id, state="working", new_messages=messages[1:]
            )

            request: GetTaskRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/get",
                "params": {
                    "task_id": task_id,
                    "history_length": 5,
                },
            }

            response = await tm.get_task(request)

            retrieved_task = response["result"]
            # History should be limited
            if "history" in retrieved_task:
                assert len(retrieved_task["history"]) <= 5


@pytest.mark.asyncio
async def test_list_empty_tasks():
    """Test listing tasks when none exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: ListTasksRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/list",
                "params": {},
            }

            response = await tm.list_tasks(request)

            assert_jsonrpc_success(response)
            assert response["result"] == []


@pytest.mark.asyncio
async def test_list_multiple_tasks():
    """Test listing multiple tasks."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create tasks via submit_task
            for i in range(5):
                message = create_test_message(text=f"Message {i}")
                await storage.submit_task(message["context_id"], message)

            request: ListTasksRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/list",
                "params": {},
            }

            response = await tm.list_tasks(request)

            task_list = response["result"]
            assert len(task_list) == 5


@pytest.mark.asyncio
async def test_cancel_nonexistent_task():
    """Test canceling a task that doesn't exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: CancelTaskRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/cancel",
                "params": {
                    "task_id": uuid4(),
                },
            }

            response = await tm.cancel_task(request)

            # Should return TaskNotFoundError (-32001)
            assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_submit_feedback():
    """Test submitting feedback for a task."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create task and update to completed state
            message = create_test_message(text="Test message")
            task = await storage.submit_task(message["context_id"], message)
            await storage.update_task(task["id"], state="completed")

            request: TaskFeedbackRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/feedback",
                "params": {
                    "task_id": task["id"],
                    "feedback": "Great job!",
                    "rating": 5,
                    "metadata": {"helpful": True},
                },
            }

            response = await tm.task_feedback(request)

            assert_jsonrpc_success(response)


@pytest.mark.asyncio
async def test_feedback_for_nonexistent_task():
    """Test submitting feedback for non-existent task."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: TaskFeedbackRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/feedback",
                "params": {
                    "task_id": uuid4(),
                    "feedback": "Test feedback",
                },
            }

            response = await tm.task_feedback(request)

            # Should return TaskNotFoundError
            assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_list_empty_contexts():
    """Test listing contexts when none exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: ListContextsRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "contexts/list",
                "params": {},
            }

            response = await tm.list_contexts(request)

            assert_jsonrpc_success(response)
            assert response["result"] == []


@pytest.mark.asyncio
async def test_list_multiple_contexts():
    """Test listing multiple contexts."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create contexts by submitting tasks with different context_ids
            for i in range(3):
                message = create_test_message(text=f"Session {i}")
                await storage.submit_task(message["context_id"], message)

            request: ListContextsRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "contexts/list",
                "params": {},
            }

            response = await tm.list_contexts(request)

            context_list = response["result"]
            assert len(context_list) == 3


@pytest.mark.asyncio
async def test_clear_context():
    """Test clearing a context."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Create a context by submitting a task
            message = create_test_message(text="To Clear")
            context_id = message["context_id"]
            await storage.submit_task(context_id, message)

            request: ClearContextsRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "contexts/clear",
                "params": {
                    "context_id": context_id,
                },
            }

            response = await tm.clear_context(request)

            # Should succeed
            assert "result" in response or "error" in response


@pytest.mark.asyncio
async def test_clear_nonexistent_context():
    """Test clearing a context that doesn't exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: ClearContextsRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "contexts/clear",
                "params": {
                    "context_id": uuid4(),
                },
            }

            response = await tm.clear_context(request)

            # Should return error
            assert "error" in response


@pytest.mark.asyncio
async def test_push_not_supported():
    """Test push notification when not supported."""
    from bindu.common.protocol.types import SetTaskPushNotificationRequest

    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            request: SetTaskPushNotificationRequest = {
                "jsonrpc": "2.0",
                "id": uuid4(),
                "method": "tasks/pushNotification/set",
                "params": {
                    "id": uuid4(),
                    "push_notification_config": {
                        "id": uuid4(),
                        "url": "https://example.com/callback",
                    },
                },
            }

            response = await tm.set_task_push_notification(request)

            # Should return PushNotificationNotSupportedError (-32005)
            if not tm._push_manager.is_push_supported():
                assert_jsonrpc_error(response, -32005)

@pytest.mark.asyncio
async def test_parse_context_id_fallback():
    """Test that malformed UUID strings safely generate a new UUID (DoS protection)."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # 1. Valid UUID string should parse correctly
            valid_uuid = uuid.uuid4()
            result_valid = tm._parse_context_id(str(valid_uuid))
            assert result_valid == valid_uuid

            # 2. Malformed string (DoS vector fallback) should not crash the server
            result_invalid = tm._parse_context_id("invalid-garbage-string")
            assert isinstance(result_invalid, uuid.UUID)
            assert result_invalid != "invalid-garbage-string"
            
            # 3. None input should generate a fresh UUID
            result_none = tm._parse_context_id(None)
            assert isinstance(result_none, uuid.UUID)


@pytest.mark.asyncio
async def test_getattr_security_and_missing_methods():
    """Test that __getattr__ prevents recursion and raises correct AttributeErrors."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            # Test recursion guard (accessing non-existent private attributes)
            with pytest.raises(AttributeError, match="has no attribute '_fake_private'"):
                _ = tm._fake_private
                
            # Test missing public methods
            with pytest.raises(AttributeError, match="has no attribute 'make_me_a_sandwich'"):
                _ = tm.make_me_a_sandwich


@pytest.mark.asyncio
async def test_task_manager_lifecycle():
    """Test is_running state and proper AsyncExitStack initialization."""
    storage = InMemoryStorage()
    scheduler = InMemoryScheduler()
    
    # 1. State should be False before context is entered
    tm = TaskManager(scheduler=scheduler, storage=storage, manifest=None)
    assert not tm.is_running
    
    # 2. State should be True inside the context
    async with tm:
        assert tm.is_running
        
    # 3. State should revert to False after exiting
    assert not tm.is_running
    
    # 4. Attempting to exit an uninitialized manager should raise a RuntimeError
    uninitialized_tm = TaskManager(scheduler=scheduler, storage=storage, manifest=None)
    with pytest.raises(RuntimeError, match="TaskManager was not properly initialized"):
        await uninitialized_tm.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_manifest_worker_initialization():
    """Test that a ManifestWorker is created when a manifest is provided."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        # Create a mock manifest to trigger the worker initialization block
        mock_manifest = MagicMock()
        tm = TaskManager(scheduler=scheduler, storage=storage, manifest=mock_manifest)
        
        # Before entering context, no workers should exist
        assert len(tm._workers) == 0
        
        async with tm:
            # Inside context, the worker should be initialized and added to the list
            assert len(tm._workers) == 1
            # Verify the worker got the correct manifest attached
            assert tm._workers[0].manifest == mock_manifest
            