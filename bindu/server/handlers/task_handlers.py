# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Task handlers for Bindu server.

This module handles task-related RPC requests including
getting, listing, canceling tasks, and submitting feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bindu.common.protocol.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    GetTaskRequest,
    GetTaskResponse,
    ListTasksRequest,
    ListTasksResponse,
    PauseTaskRequest,
    PauseTaskResponse,
    ResumeTaskRequest,
    ResumeTaskResponse,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
    TaskNotCancelableError,
    TaskNotFoundError,
)
from bindu.settings import app_settings

from bindu.utils.task_telemetry import trace_task_operation, track_active_task

from bindu.server.scheduler import Scheduler
from bindu.server.storage import Storage


@dataclass
class TaskHandlers:
    """Handles task-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    error_response_creator: Any = None

    @trace_task_operation("get_task")
    async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Get a task and return it to the client."""
        task_id = request["params"]["task_id"]
        history_length = request["params"].get("history_length")
        task = await self.storage.load_task(task_id, history_length)

        if task is None:
            return self.error_response_creator(
                GetTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        return GetTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("cancel_task")
    @track_active_task
    async def cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        """Cancel a running task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                CancelTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        # Check if task is in a cancelable state
        current_state = task["status"]["state"]

        if current_state in app_settings.agent.terminal_states:
            return self.error_response_creator(
                CancelTaskResponse,
                request["id"],
                TaskNotCancelableError,
                f"Task cannot be canceled in '{current_state}' state. "
                f"Tasks can only be canceled while pending or running.",
            )

        # Cancel the task
        await self.scheduler.cancel_task(request["params"])
        task = await self.storage.load_task(task_id)

        return CancelTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("pause_task")
    async def pause_task(self, request: PauseTaskRequest) -> PauseTaskResponse:
        """Pause a running task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                PauseTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        # Check if task is in a pausable state
        current_state = task["status"]["state"]
        # Pausable states: working, input-required, auth-required
        # We allow pausing in these states.
        # Check against app_settings if needed, but logic is:
        # If it's in terminal state, can't pause.
        # If it's already paused, return success or error (idempotent preferable, but user might want error).

        if current_state in app_settings.agent.terminal_states:
            return self.error_response_creator(
                PauseTaskResponse,
                request["id"],
                TaskNotCancelableError,
                f"Task cannot be paused in '{current_state}' state. ",
            )

        if current_state == "paused":
            # Already paused, just return the task
            return PauseTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

        # Execute pause via scheduler (which calls worker)
        # Note: scheduler must have pause_task method.
        # Assuming scheduler propagates to worker.
        await self.scheduler.pause_task(request["params"])

        # Reload task to get updated state
        task = await self.storage.load_task(task_id)
        return PauseTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("resume_task")
    async def resume_task(self, request: ResumeTaskRequest) -> ResumeTaskResponse:
        """Resume a paused task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                ResumeTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        current_state = task["status"]["state"]

        if current_state != "paused":
            return self.error_response_creator(
                ResumeTaskResponse,
                request["id"],
                TaskNotCancelableError,
                f"Task cannot be resumed from '{current_state}' state. Only paused tasks can be resumed.",
            )

        # Execute resume
        await self.scheduler.resume_task(request["params"])

        task = await self.storage.load_task(task_id)
        return ResumeTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("list_tasks", include_params=False)
    async def list_tasks(self, request: ListTasksRequest) -> ListTasksResponse:
        """List all tasks in storage."""
        tasks = await self.storage.list_tasks(request["params"].get("length"))

        if tasks is None:
            return self.error_response_creator(
                ListTasksResponse, request["id"], TaskNotFoundError, "No tasks found"
            )

        return ListTasksResponse(jsonrpc="2.0", id=request["id"], result=tasks)

    @trace_task_operation("task_feedback")
    async def task_feedback(self, request: TaskFeedbackRequest) -> TaskFeedbackResponse:
        """Submit feedback for a completed task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                TaskFeedbackResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        feedback_data = {
            "task_id": task_id,
            "feedback": request["params"]["feedback"],
            "rating": request["params"]["rating"],
            "metadata": request["params"]["metadata"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if hasattr(self.storage, "store_task_feedback"):
            await self.storage.store_task_feedback(task_id, feedback_data)

        return TaskFeedbackResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "message": "Feedback submitted successfully",
                "task_id": str(task_id),
            },
        )
