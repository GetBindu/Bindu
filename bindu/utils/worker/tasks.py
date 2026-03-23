"""Task state management utilities for worker operations."""

from __future__ import annotations

from bindu.common.protocol.types import Task


class TaskStateManager:
    """Optimized manager for task state transitions and validation."""

    @staticmethod
    async def validate_task_state(
        task: Task, expected_state: str = "submitted"
    ) -> None:
        """Validate task is in expected state.

        Args:
            task: Task dictionary
            expected_state: Expected task state

        Raises:
            ValueError: If task state doesn't match expected
        """
        current_state = task["status"]["state"]
        if current_state != expected_state:
            raise ValueError(
                f"Task {task['id']} already processed (state: {current_state}, expected: {expected_state})"
            )
