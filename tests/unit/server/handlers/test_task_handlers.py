"""Minimal tests for task handlers."""

from unittest.mock import AsyncMock, Mock
import pytest

from bindu.server.handlers.task_handlers import TaskHandlers


class TestTaskHandlers:
    """Test task handler functionality."""

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test getting task successfully."""
        mock_storage = AsyncMock()
        mock_task = {"id": "task123", "status": {"state": "completed"}}
        mock_storage.load_task.return_value = mock_task

        handler = TaskHandlers(scheduler=Mock(), storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "1", "params": {"task_id": "task123"}}

        response = await handler.get_task(request)

        assert response["jsonrpc"] == "2.0"
        assert response["result"]["id"] == "task123"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting non-existent task."""
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None

        mock_error_creator = Mock(return_value={"error": "not found"})
        handler = TaskHandlers(
            scheduler=Mock(),
            storage=mock_storage,
            error_response_creator=mock_error_creator,
        )
        request = {"jsonrpc": "2.0", "id": "2", "params": {"task_id": "invalid"}}

        response = await handler.get_task(request)

        assert "error" in response

    @pytest.mark.asyncio
    async def test_list_tasks_success(self):
        """Test listing tasks successfully."""
        mock_storage = AsyncMock()
        mock_storage.list_tasks.return_value = [
            {"id": "task1", "status": {"state": "running"}},
            {"id": "task2", "status": {"state": "completed"}},
        ]

        handler = TaskHandlers(scheduler=Mock(), storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "3", "params": {"length": 10}}

        response = await handler.list_tasks(request)

        assert len(response["result"]) == 2

    @pytest.mark.asyncio
    async def test_task_feedback_success(self):
        """Test submitting task feedback."""
        mock_storage = AsyncMock()
        mock_task = {"id": "task123", "status": {"state": "completed"}}
        mock_storage.load_task.return_value = mock_task
        mock_storage.store_task_feedback = AsyncMock()

        handler = TaskHandlers(scheduler=Mock(), storage=mock_storage)
        request = {
            "jsonrpc": "2.0",
            "id": "4",
            "params": {
                "task_id": "task123",
                "feedback": "Great!",
                "rating": 5,
                "metadata": {},
            },
        }

        response = await handler.task_feedback(request)

        assert "Feedback submitted successfully" in response["result"]["message"]
        mock_storage.store_task_feedback.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_task_terminal_state(self):
        """Test canceling task in terminal state returns error."""
        mock_storage = AsyncMock()
        mock_task = {"id": "task123", "status": {"state": "completed"}}
        mock_storage.load_task.return_value = mock_task
        mock_scheduler = AsyncMock()

        mock_error_creator = Mock(return_value={"error": "not cancelable"})
        handler = TaskHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            error_response_creator=mock_error_creator,
        )
        request = {
            "jsonrpc": "2.0",
            "id": "6",
            "params": {"task_id": "task123"},
        }

        response = await handler.cancel_task(request)

        assert "error" in response
        mock_scheduler.cancel_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test canceling non-existent task."""
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None
        mock_scheduler = AsyncMock()

        mock_error_creator = Mock(return_value={"error": "not found"})
        handler = TaskHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            error_response_creator=mock_error_creator,
        )
        request = {
            "jsonrpc": "2.0",
            "id": "7",
            "params": {"task_id": "invalid"},
        }

        response = await handler.cancel_task(request)

        assert "error" in response
        mock_scheduler.cancel_task.assert_not_called()
