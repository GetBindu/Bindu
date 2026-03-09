# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for TaskHandlers.

Covers get_task, cancel_task, list_tasks, and task_feedback
RPC dispatch methods in isolation using InMemoryStorage/InMemoryScheduler.
"""

from uuid import uuid4

import pytest

from unittest.mock import AsyncMock, MagicMock

from bindu.common.protocol.types import (
    CancelTaskRequest,
    GetTaskRequest,
    ListTasksRequest,
    TaskFeedbackRequest,
)
from bindu.server.handlers.task_handlers import TaskHandlers
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.utils import (
    assert_jsonrpc_error,
    assert_jsonrpc_success,
    create_test_message,
)


def _mock_scheduler():
    """Return a scheduler stub that never blocks on cancel/run."""
    sched = MagicMock()
    sched.cancel_task = AsyncMock(return_value=None)
    sched.run_task = AsyncMock(return_value=None)
    return sched


def _make_error_response(response_class, request_id, error_class, message):
    """Mirror TaskManager._create_error_response for handler tests."""
    return response_class(
        jsonrpc="2.0",
        id=request_id,
        error=error_class(code=-32001, message=message),
    )


def _make_handlers(storage, scheduler):
    return TaskHandlers(
        scheduler=scheduler,
        storage=storage,
        error_response_creator=_make_error_response,
    )


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_task_returns_existing_task():
    """get_task returns the task when it exists in storage."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="hello")
        await storage.submit_task(message["context_id"], message)

        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {"task_id": message["task_id"]},
        }

        response = await handlers.get_task(request)
        assert_jsonrpc_success(response)
        assert response["result"]["id"] == message["task_id"]


@pytest.mark.asyncio
async def test_get_task_not_found_returns_error():
    """get_task returns error (-32001) for an unknown task ID."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {"task_id": uuid4()},
        }

        response = await handlers.get_task(request)
        assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_get_task_with_history_length():
    """get_task forwards history_length param to storage without error."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="history test")
        await storage.submit_task(message["context_id"], message)

        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {"task_id": message["task_id"], "history_length": 5},
        }

        response = await handlers.get_task(request)
        assert_jsonrpc_success(response)


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tasks_empty_storage():
    """list_tasks returns an empty list when no tasks exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        request: ListTasksRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/list",
            "params": {},
        }

        response = await handlers.list_tasks(request)
        assert_jsonrpc_success(response)
        assert response["result"] == []


@pytest.mark.asyncio
async def test_list_tasks_returns_all_tasks():
    """list_tasks returns every submitted task."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        msg1 = create_test_message(text="first")
        msg2 = create_test_message(text="second")
        await storage.submit_task(msg1["context_id"], msg1)
        await storage.submit_task(msg2["context_id"], msg2)

        request: ListTasksRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/list",
            "params": {},
        }

        response = await handlers.list_tasks(request)
        assert_jsonrpc_success(response)
        assert len(response["result"]) == 2


@pytest.mark.asyncio
async def test_list_tasks_with_length_limit():
    """list_tasks respects an optional length parameter."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        for i in range(5):
            msg = create_test_message(text=f"msg {i}")
            await storage.submit_task(msg["context_id"], msg)

        request: ListTasksRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/list",
            "params": {"length": 3},
        }

        response = await handlers.list_tasks(request)
        assert_jsonrpc_success(response)
        assert len(response["result"]) <= 3


# ---------------------------------------------------------------------------
# cancel_task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_task_not_found_returns_error():
    """cancel_task returns error when the task does not exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {"task_id": uuid4()},
        }

        response = await handlers.cancel_task(request)
        assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_cancel_task_in_terminal_state_returns_error():
    """cancel_task returns an error when task is already completed."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="complete me")
        await storage.submit_task(message["context_id"], message)
        await storage.update_task(message["task_id"], state="completed")

        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {"task_id": message["task_id"]},
        }

        response = await handlers.cancel_task(request)
        assert "error" in response


@pytest.mark.asyncio
async def test_cancel_task_submitted_state():
    """cancel_task succeeds when the task is in submitted (non-terminal) state.

    The real InMemoryScheduler uses an anyio channel that blocks without a
    consumer, so we use a mock scheduler here to keep the test fast.
    """
    storage = InMemoryStorage()
    scheduler = _mock_scheduler()
    handlers = _make_handlers(storage, scheduler)

    message = create_test_message(text="cancel me")
    await storage.submit_task(message["context_id"], message)

    request: CancelTaskRequest = {
        "jsonrpc": "2.0",
        "id": uuid4(),
        "method": "tasks/cancel",
        "params": {"task_id": message["task_id"]},
    }

    response = await handlers.cancel_task(request)
    assert_jsonrpc_success(response)
    scheduler.cancel_task.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_already_failed_task_returns_error():
    """cancel_task returns an error for a task already in failed state."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="failed task")
        await storage.submit_task(message["context_id"], message)
        await storage.update_task(message["task_id"], state="failed")

        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {"task_id": message["task_id"]},
        }

        response = await handlers.cancel_task(request)
        assert "error" in response


# ---------------------------------------------------------------------------
# task_feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_feedback_stores_successfully():
    """task_feedback accepts and stores feedback for an existing task."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="rate me")
        await storage.submit_task(message["context_id"], message)

        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": message["task_id"],
                "feedback": "Great response!",
                "rating": 5,
                "metadata": {},
            },
        }

        response = await handlers.task_feedback(request)
        assert_jsonrpc_success(response)
        assert response["result"]["task_id"] == str(message["task_id"])


@pytest.mark.asyncio
async def test_task_feedback_task_not_found():
    """task_feedback returns error when task does not exist."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": uuid4(),
                "feedback": "Nice",
                "rating": 4,
                "metadata": {},
            },
        }

        response = await handlers.task_feedback(request)
        assert_jsonrpc_error(response, -32001)


@pytest.mark.asyncio
async def test_task_feedback_low_rating():
    """task_feedback handles minimum rating (1) without error."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="not great")
        await storage.submit_task(message["context_id"], message)

        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": message["task_id"],
                "feedback": "Poor performance",
                "rating": 1,
                "metadata": {"source": "user"},
            },
        }

        response = await handlers.task_feedback(request)
        assert_jsonrpc_success(response)


@pytest.mark.asyncio
async def test_task_feedback_with_metadata():
    """task_feedback persists arbitrary metadata alongside the rating."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        handlers = _make_handlers(storage, scheduler)

        message = create_test_message(text="metadata test")
        await storage.submit_task(message["context_id"], message)

        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": message["task_id"],
                "feedback": "Helpful",
                "rating": 4,
                "metadata": {"session": "abc123", "ui": "chat"},
            },
        }

        response = await handlers.task_feedback(request)
        assert_jsonrpc_success(response)
