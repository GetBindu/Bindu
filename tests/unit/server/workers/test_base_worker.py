"""Tests for Worker base class pause/resume handlers."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from bindu.server.workers.manifest_worker import ManifestWorker
from bindu.common.protocol.types import TaskIdParams


@pytest_asyncio.fixture
async def mock_worker():
    """Create a ManifestWorker instance with mocked dependencies."""
    worker = ManifestWorker.__new__(ManifestWorker)
    worker.storage = AsyncMock()
    worker.scheduler = AsyncMock()
    worker._task_handlers = None
    return worker


@pytest.fixture
def task_id():
    return str(uuid4())


class TestHandlePause:
    """Tests for _handle_pause method."""

    @pytest.mark.asyncio
    async def test_pause_task_success(self, mock_worker, task_id):
        """Test successful pause operation."""
        mock_worker.storage.load_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": {"state": "working", "checkpoint": "step-5"},
                "metadata": {},
                "context_id": str(uuid4()),
            }
        )
        mock_worker.storage.update_task = AsyncMock()
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_pause(params)

        mock_worker.storage.load_task.assert_called_once_with(task_id)
        mock_worker.storage.update_task.assert_called_once()
        call_kwargs = mock_worker.storage.update_task.call_args[1]
        assert call_kwargs["state"] == "suspended"
        assert "paused_at" in call_kwargs["metadata"]
        assert call_kwargs["metadata"]["pause_checkpoint"] == "step-5"

    @pytest.mark.asyncio
    async def test_pause_task_not_found(self, mock_worker, task_id):
        """Test pause when task doesn't exist."""
        mock_worker.storage.load_task = AsyncMock(return_value=None)
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_pause(params)

        mock_worker.storage.load_task.assert_called_once_with(task_id)
        mock_worker.storage.update_task.assert_not_called()


class TestHandleResume:
    """Tests for _handle_resume method."""

    @pytest.mark.asyncio
    async def test_resume_task_success(self, mock_worker, task_id):
        """Test successful resume operation."""
        context_id = str(uuid4())
        history_message = {"role": "user", "content": "Hello"}

        mock_worker.storage.load_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": {"state": "suspended"},
                "metadata": {"paused_at": "2024-01-01T00:00:00"},
                "context_id": context_id,
                "history": [history_message],
            }
        )
        mock_worker.storage.update_task = AsyncMock()
        mock_worker.scheduler.run_task = AsyncMock()
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_resume(params)

        mock_worker.storage.load_task.assert_called_once_with(task_id)
        mock_worker.storage.update_task.assert_called_once()
        call_kwargs = mock_worker.storage.update_task.call_args[1]
        assert call_kwargs["state"] == "resumed"
        assert "resumed_at" in call_kwargs["metadata"]
        mock_worker.scheduler.run_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_task_not_found(self, mock_worker, task_id):
        """Test resume when task doesn't exist."""
        mock_worker.storage.load_task = AsyncMock(return_value=None)
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_resume(params)

        mock_worker.storage.load_task.assert_called_once_with(task_id)
        mock_worker.storage.update_task.assert_not_called()
        mock_worker.scheduler.run_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_task_no_history(self, mock_worker, task_id):
        """Test resume when task has no history."""
        context_id = str(uuid4())

        mock_worker.storage.load_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": {"state": "suspended"},
                "metadata": {},
                "context_id": context_id,
                "history": [],  # Empty history
            }
        )
        mock_worker.storage.update_task = AsyncMock()
        mock_worker.scheduler.run_task = AsyncMock()
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_resume(params)

        # Should still update state and call run_task (with None message)
        mock_worker.storage.update_task.assert_called_once()
        mock_worker.scheduler.run_task.assert_called_once()
        # Verify run_task was called (message may be None or passed positionally)
        call_args = mock_worker.scheduler.run_task.call_args[0]
        assert len(call_args) == 1  # Called with one positional argument (TaskSendParams)

    @pytest.mark.asyncio
    async def test_resume_task_with_metadata(self, mock_worker, task_id):
        """Test resume preserves and updates metadata."""
        context_id = str(uuid4())
        history_message = {"role": "user", "content": "Hello"}

        mock_worker.storage.load_task = AsyncMock(
            return_value={
                "id": task_id,
                "status": {"state": "suspended"},
                "metadata": {"original_key": "original_value", "paused_at": "2024-01-01T00:00:00"},
                "context_id": context_id,
                "history": [history_message],
            }
        )
        mock_worker.storage.update_task = AsyncMock()
        mock_worker.scheduler.run_task = AsyncMock()
        mock_worker._normalize_uuid = lambda x: task_id

        params: TaskIdParams = {"task_id": task_id}
        await mock_worker._handle_resume(params)

        # Verify metadata is preserved and updated
        call_kwargs = mock_worker.storage.update_task.call_args[1]
        assert call_kwargs["metadata"]["original_key"] == "original_value"
        assert call_kwargs["metadata"]["paused_at"] == "2024-01-01T00:00:00"
        assert "resumed_at" in call_kwargs["metadata"]