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
    async def get_task(
        self,
        request: GetTaskRequest,
        caller_did: str | None = None,
    ) -> GetTaskResponse:
        """Get a task and return it to the client.

        Returns ``TaskNotFoundError`` for both "truly missing" and "exists but
        owned by another caller" — the error shape intentionally cannot be
        used to probe for task IDs across tenants.
        """
        task_id = request["params"]["task_id"]
        history_length = request["params"].get("history_length")
        task = await self.storage.load_task(task_id, history_length)

        if task is None:
            return self.error_response_creator(
                GetTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        owner = await self.storage.get_task_owner(task_id)
        if owner != caller_did:
            return self.error_response_creator(
                GetTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        return GetTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("cancel_task")
    @track_active_task
    async def cancel_task(
        self,
        request: CancelTaskRequest,
        caller_did: str | None = None,
    ) -> CancelTaskResponse:
        """Cancel a running task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                CancelTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        owner = await self.storage.get_task_owner(task_id)
        if owner != caller_did:
            # Same error as "not found" so a caller cannot discover which
            # task IDs belong to other tenants by trying to cancel them.
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

        # Type narrowing: task should exist since we already validated it above
        assert task is not None

        return CancelTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("list_tasks", include_params=False)
    async def list_tasks(
        self,
        request: ListTasksRequest,
        caller_did: str | None = None,
    ) -> ListTasksResponse:
        """List tasks owned by the caller.

        When ``caller_did`` is non-None, the storage layer filters at the
        index so only the caller's tasks are returned. When ``caller_did`` is
        None (auth disabled), the current unfiltered behavior is preserved.
        """
        tasks = await self.storage.list_tasks(
            request["params"].get("length"), owner_did=caller_did
        )

        if tasks is None:
            return self.error_response_creator(
                ListTasksResponse, request["id"], TaskNotFoundError, "No tasks found"
            )

        return ListTasksResponse(jsonrpc="2.0", id=request["id"], result=tasks)

    @trace_task_operation("task_feedback")
    async def task_feedback(
        self,
        request: TaskFeedbackRequest,
        caller_did: str | None = None,
    ) -> TaskFeedbackResponse:
        """Submit feedback for a completed task.

        Only the task owner can submit feedback.
        """
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self.error_response_creator(
                TaskFeedbackResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        owner = await self.storage.get_task_owner(task_id)
        if owner != caller_did:
            return self.error_response_creator(
                TaskFeedbackResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        # Timestamp is always stored in UTC ISO-8601 format for consistency
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
