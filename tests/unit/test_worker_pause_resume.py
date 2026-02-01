"""Unit tests for Worker pause and resume operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from bindu.common.protocol.types import TaskIdParams
from bindu.server.workers.base import Worker
from bindu.server.scheduler.base import Scheduler
from bindu.server.storage.base import Storage


class MockWorker(Worker):
    """Mock worker implementation for testing pause/resume."""

    async def run_task(self, params):
        """Mock run_task implementation."""
        pass

    async def cancel_task(self, params):
        """Mock cancel_task implementation."""
        pass

    def build_message_history(self, history):
        """Mock build_message_history implementation."""
        return []

    def build_artifacts(self, result):
        """Mock build_artifacts implementation."""
        return []


@pytest.fixture
def mock_storage():
    """Create a mock storage instance."""
    storage = AsyncMock(spec=Storage)
    return storage


@pytest.fixture
def mock_scheduler():
    """Create a mock scheduler instance."""
    scheduler = MagicMock(spec=Scheduler)
    return scheduler


@pytest.fixture
def worker(mock_storage, mock_scheduler):
    """Create a worker instance with mocked dependencies."""
    return MockWorker(scheduler=mock_scheduler, storage=mock_storage)


class TestWorkerPause:
    """Test suite for task pause operation."""

    @pytest.mark.asyncio
    async def test_pause_working_task_success(self, worker, mock_storage):
        """Test successfully pausing a task in 'working' state."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "working"},
        }

        mock_storage.load_task.return_value = task
        mock_storage.update_task.return_value = task

        params = TaskIdParams(task_id=task_id)
        await worker._handle_pause(params)

        # Verify task was loaded
        mock_storage.load_task.assert_called_once_with(task_id)

        # Verify task state was updated to suspended
        mock_storage.update_task.assert_called_once_with(task_id, state="suspended")

    @pytest.mark.asyncio
    async def test_pause_input_required_task_success(self, worker, mock_storage):
        """Test successfully pausing a task in 'input-required' state."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "input-required"},
        }

        mock_storage.load_task.return_value = task
        mock_storage.update_task.return_value = task

        params = TaskIdParams(task_id=task_id)
        await worker._handle_pause(params)

        mock_storage.update_task.assert_called_once_with(task_id, state="suspended")

    @pytest.mark.asyncio
    async def test_pause_auth_required_task_success(self, worker, mock_storage):
        """Test successfully pausing a task in 'auth-required' state."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "auth-required"},
        }

        mock_storage.load_task.return_value = task
        mock_storage.update_task.return_value = task

        params = TaskIdParams(task_id=task_id)
        await worker._handle_pause(params)

        mock_storage.update_task.assert_called_once_with(task_id, state="suspended")

    @pytest.mark.asyncio
    async def test_pause_task_not_found(self, worker, mock_storage):
        """Test pausing a non-existent task raises ValueError."""
        task_id = uuid4()
        mock_storage.load_task.return_value = None

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(ValueError, match=f"Task {task_id} not found"):
            await worker._handle_pause(params)

        # Verify update was not called
        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_submitted_task_raises_error(self, worker, mock_storage):
        """Test pausing a task in 'submitted' state raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "submitted"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot pause task in state 'submitted'",
        ):
            await worker._handle_pause(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_completed_task_raises_error(self, worker, mock_storage):
        """Test pausing a completed task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "completed"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot pause task in state 'completed'",
        ):
            await worker._handle_pause(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_failed_task_raises_error(self, worker, mock_storage):
        """Test pausing a failed task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "failed"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot pause task in state 'failed'",
        ):
            await worker._handle_pause(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_canceled_task_raises_error(self, worker, mock_storage):
        """Test pausing a canceled task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "canceled"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot pause task in state 'canceled'",
        ):
            await worker._handle_pause(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_suspended_task_raises_error(self, worker, mock_storage):
        """Test pausing an already suspended task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "suspended"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot pause task in state 'suspended'",
        ):
            await worker._handle_pause(params)

        mock_storage.update_task.assert_not_called()


class TestWorkerResume:
    """Test suite for task resume operation."""

    @pytest.mark.asyncio
    async def test_resume_suspended_task_success(self, worker, mock_storage):
        """Test successfully resuming a suspended task."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "suspended"},
        }

        mock_storage.load_task.return_value = task
        mock_storage.update_task.return_value = task

        params = TaskIdParams(task_id=task_id)
        await worker._handle_resume(params)

        # Verify task was loaded
        mock_storage.load_task.assert_called_once_with(task_id)

        # Verify task state was updated to resumed
        mock_storage.update_task.assert_called_once_with(task_id, state="resumed")

    @pytest.mark.asyncio
    async def test_resume_task_not_found(self, worker, mock_storage):
        """Test resuming a non-existent task raises ValueError."""
        task_id = uuid4()
        mock_storage.load_task.return_value = None

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(ValueError, match=f"Task {task_id} not found"):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_working_task_raises_error(self, worker, mock_storage):
        """Test resuming a task in 'working' state raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "working"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'working'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_completed_task_raises_error(self, worker, mock_storage):
        """Test resuming a completed task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "completed"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'completed'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_failed_task_raises_error(self, worker, mock_storage):
        """Test resuming a failed task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "failed"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'failed'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_canceled_task_raises_error(self, worker, mock_storage):
        """Test resuming a canceled task raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "canceled"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'canceled'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_submitted_task_raises_error(self, worker, mock_storage):
        """Test resuming a task in 'submitted' state raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "submitted"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'submitted'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_input_required_task_raises_error(self, worker, mock_storage):
        """Test resuming a task in 'input-required' state raises ValueError."""
        task_id = uuid4()
        task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "input-required"},
        }

        mock_storage.load_task.return_value = task

        params = TaskIdParams(task_id=task_id)

        with pytest.raises(
            ValueError,
            match="Cannot resume task in state 'input-required'",
        ):
            await worker._handle_resume(params)

        mock_storage.update_task.assert_not_called()


class TestPauseResumeWorkflow:
    """Test pause/resume workflow integration."""

    @pytest.mark.asyncio
    async def test_pause_resume_workflow(self, worker, mock_storage):
        """Test complete pause-resume workflow."""
        task_id = uuid4()
        working_task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "working"},
        }
        suspended_task = {
            "id": task_id,
            "context_id": uuid4(),
            "status": {"state": "suspended"},
        }

        # Set up storage mock to return appropriate task state
        mock_storage.load_task.side_effect = [working_task, suspended_task]
        mock_storage.update_task.return_value = None

        params = TaskIdParams(task_id=task_id)

        # Step 1: Pause working task
        await worker._handle_pause(params)
        assert mock_storage.update_task.call_count == 1
        mock_storage.update_task.assert_called_with(task_id, state="suspended")

        # Step 2: Resume suspended task
        await worker._handle_resume(params)
        assert mock_storage.update_task.call_count == 2
        mock_storage.update_task.assert_called_with(task_id, state="resumed")
