"""Tests for worker task utilities."""

import pytest
from typing import cast
from uuid import uuid4

from bindu.common.protocol.types import Task
from bindu.utils.worker.tasks import TaskStateManager


class TestTaskStateManager:
    """Test TaskStateManager functionality."""

    @pytest.mark.asyncio
    async def test_validate_task_state_matches_expected(self):
        """Test validating task with matching state."""
        task = cast(
            Task,
            {
                "id": uuid4(),
                "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        # Should not raise when state matches expected
        await TaskStateManager.validate_task_state(task, expected_state="submitted")

    @pytest.mark.asyncio
    async def test_validate_task_state_custom_expected(self):
        """Test validating task with custom expected state."""
        task = cast(
            Task,
            {
                "id": uuid4(),
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        # Should not raise when state matches custom expected
        await TaskStateManager.validate_task_state(task, expected_state="working")

    @pytest.mark.asyncio
    async def test_validate_task_state_mismatch_raises(self):
        """Test validating task with mismatched state raises error."""
        task = cast(
            Task,
            {
                "id": uuid4(),
                "status": {"state": "completed", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        # Should raise when state doesn't match expected
        with pytest.raises(ValueError, match="already processed"):
            await TaskStateManager.validate_task_state(task, expected_state="submitted")
