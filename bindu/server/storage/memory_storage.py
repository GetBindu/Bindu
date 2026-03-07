"""In-memory storage implementation for A2A protocol task and context management.

This implementation provides a simple, non-persistent storage backend suitable for:
- Development and testing
- Prototyping agents
- Single-session applications

Hybrid Agent Pattern Support:
- Stores tasks with flexible state transitions (working → input-required → completed)
- Maintains conversation context across multiple tasks
- Supports incremental message history updates
- Enables task refinements through context-based task lookup

Note: All data is lost when the application stops. Use persistent storage for production.
"""

from __future__ import annotations as _annotations

import copy
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from typing_extensions import TypeVar

from bindu.common.protocol.types import (
    Artifact,
    Message,
    PushNotificationConfig,
    Task,
    TaskState,
    TaskStatus,
)
from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.utils.retry import retry_storage_operation

from .base import Storage

logger = get_logger("bindu.server.storage.memory_storage")

ContextT = TypeVar("ContextT", default=Any)


class InMemoryStorage(Storage[ContextT]):
    """In-memory storage implementation for tasks and contexts.

    Storage Structure:
    - tasks: Dict[UUID, Task] - All tasks indexed by task_id
    - contexts: Dict[UUID, list[UUID]] - Task IDs grouped by context_id
    - task_feedback: Dict[UUID, List[dict]] - Optional feedback storage
    - _checkpoints: Dict[UUID, list] - Checkpoints for pause/resume
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self.tasks: dict[UUID, Task] = {}
        self.contexts: dict[UUID, list[UUID]] = {}
        self.task_feedback: dict[UUID, list[dict[str, Any]]] = {}
        self._webhook_configs: dict[UUID, PushNotificationConfig] = {}
        self._checkpoints: dict[UUID, list[dict[str, Any]]] = {}

    @retry_storage_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from memory.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        task = self.tasks.get(task_id)
        if task is None:
            return None

        task_copy = cast(Task, copy.deepcopy(task))

        if history_length is not None and history_length > 0 and "history" in task:
            task_copy["history"] = task["history"][-history_length:]

        return task_copy

    @retry_storage_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create a new task or continue an existing non-terminal task."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        task_id_raw = message.get("task_id")
        task_id: UUID

        if isinstance(task_id_raw, str):
            task_id = UUID(task_id_raw)
        elif isinstance(task_id_raw, UUID):
            task_id = task_id_raw
        else:
            raise TypeError(
                f"task_id must be UUID or str, got {type(task_id_raw).__name__}"
            )

        message["task_id"] = task_id
        message["context_id"] = context_id

        message_id_raw = message.get("message_id")
        if isinstance(message_id_raw, str):
            message["message_id"] = UUID(message_id_raw)
        elif message_id_raw is not None and not isinstance(message_id_raw, UUID):
            raise TypeError(
                f"message_id must be UUID or str, got {type(message_id_raw).__name__}"
            )

        ref_ids_key = "reference_task_ids"
        if ref_ids_key in message:
            ref_ids = message[ref_ids_key]
            if ref_ids is not None:
                normalized_refs = []
                for ref_id in ref_ids:
                    if isinstance(ref_id, str):
                        normalized_refs.append(UUID(ref_id))
                    elif isinstance(ref_id, UUID):
                        normalized_refs.append(ref_id)
                    else:
                        raise TypeError(
                            f"reference_task_id must be UUID or str, got {type(ref_id).__name__}"
                        )
                message["reference_task_ids"] = normalized_refs

        existing_task = self.tasks.get(task_id)

        if existing_task:
            current_state = existing_task["status"]["state"]

            if current_state in app_settings.agent.terminal_states:
                raise ValueError(
                    f"Cannot continue task {task_id}: Task is in terminal state '{current_state}' and is immutable. "
                    f"Create a new task with referenceTaskIds to continue the conversation."
                )

            logger.info(
                f"Continuing existing task {task_id} from state '{current_state}'"
            )

            if "history" not in existing_task:
                existing_task["history"] = []
            existing_task["history"].append(message)

            existing_task["status"] = TaskStatus(
                state="submitted", timestamp=datetime.now(timezone.utc).isoformat()
            )

            return existing_task

        task_status = TaskStatus(
            state="submitted", timestamp=datetime.now(timezone.utc).isoformat()
        )
        task = Task(
            id=task_id,
            context_id=context_id,
            kind="task",
            status=task_status,
            history=[message],
        )
        self.tasks[task_id] = task

        if context_id not in self.contexts:
            self.contexts[context_id] = []
        self.contexts[context_id].append(task_id)

        return task

    @retry_storage_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Update task state and append new content."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        task["status"] = TaskStatus(
            state=state, timestamp=datetime.now(timezone.utc).isoformat()
        )

        if metadata:
            if "metadata" not in task:
                task["metadata"] = {}
            task["metadata"].update(metadata)

        if new_artifacts:
            if "artifacts" not in task:
                task["artifacts"] = []
            task["artifacts"].extend(new_artifacts)

        if new_messages:
            if "history" not in task:
                task["history"] = []
            for message in new_messages:
                if not isinstance(message, dict):
                    raise TypeError(
                        f"Message must be dict, got {type(message).__name__}"
                    )
                message["task_id"] = task_id
                message["context_id"] = task["context_id"]
                task["history"].append(message)

        return task

    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context metadata."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

    async def load_context(self, context_id: UUID) -> list[UUID] | None:
        """Load context task list from storage."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        return self.contexts.get(context_id)

    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        if not isinstance(messages, list):
            raise TypeError(f"messages must be list, got {type(messages).__name__}")

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks in storage."""
        if length is None:
            return list(self.tasks.values())

        all_tasks = list(self.tasks.values())
        return all_tasks[-length:] if length < len(all_tasks) else all_tasks

    async def count_tasks(self, status: str | None = None) -> int:
        """Count number of tasks, optionally filtered by status."""
        if status is None:
            return len(self.tasks)

        return sum(1 for t in self.tasks.values() if t["status"]["state"] == status)

    async def list_tasks_by_context(
        self, context_id: UUID, length: int | None = None
    ) -> list[Task]:
        """List tasks belonging to a specific context."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        task_ids = self.contexts.get(context_id, [])
        tasks: list[Task] = [
            self.tasks[task_id] for task_id in task_ids if task_id in self.tasks
        ]

        if length is not None and length > 0 and length < len(tasks):
            return tasks[-length:]
        return tasks

    async def list_contexts(self, length: int | None = None) -> list[dict[str, Any]]:
        """List all contexts in storage."""
        contexts = [
            {"context_id": ctx_id, "task_count": len(task_ids), "task_ids": task_ids}
            for ctx_id, task_ids in self.contexts.items()
        ]

        if length is not None and length > 0 and length < len(contexts):
            return contexts[-length:]
        return contexts

    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context."""
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")

        task_ids = self.contexts.get(context_id, [])

        for task_id in task_ids:
            if task_id in self.tasks:
                del self.tasks[task_id]
            if task_id in self.task_feedback:
                del self.task_feedback[task_id]

        del self.contexts[context_id]

        logger.info(f"Cleared context {context_id}: removed {len(task_ids)} tasks")

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage."""
        self.tasks.clear()
        self.contexts.clear()
        self.task_feedback.clear()
        self._webhook_configs.clear()
        self._checkpoints.clear()

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if not isinstance(feedback_data, dict):
            raise TypeError(
                f"feedback_data must be dict, got {type(feedback_data).__name__}"
            )

        if task_id not in self.task_feedback:
            self.task_feedback[task_id] = []
        self.task_feedback[task_id].append(feedback_data)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        return self.task_feedback.get(task_id)

    async def save_webhook_config(
        self, task_id: UUID, config: PushNotificationConfig
    ) -> None:
        """Save a webhook configuration for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._webhook_configs[task_id] = config
        logger.debug(f"Saved webhook config for task {task_id}")

    async def load_webhook_config(self, task_id: UUID) -> PushNotificationConfig | None:
        """Load a webhook configuration for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        return self._webhook_configs.get(task_id)

    async def delete_webhook_config(self, task_id: UUID) -> None:
        """Delete a webhook configuration for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if task_id in self._webhook_configs:
            del self._webhook_configs[task_id]
            logger.debug(f"Deleted webhook config for task {task_id}")

    async def load_all_webhook_configs(self) -> dict[UUID, PushNotificationConfig]:
        """Load all stored webhook configurations."""
        return dict(self._webhook_configs)

    async def save_checkpoint(
        self,
        task_id: UUID,
        checkpoint_data: dict[str, Any],
        step_number: int = 0,
        step_label: str | None = None,
    ) -> None:
        """Save a checkpoint for task pause/resume."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if not isinstance(checkpoint_data, dict):
            raise TypeError(
                f"checkpoint_data must be dict, got {type(checkpoint_data).__name__}"
            )

        if task_id not in self._checkpoints:
            self._checkpoints[task_id] = []

        self._checkpoints[task_id].append(
            {
                "checkpoint_data": checkpoint_data,
                "step_number": step_number,
                "step_label": step_label,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.debug(f"Saved checkpoint for task {task_id} at step {step_number}")

    async def get_checkpoint(self, task_id: UUID) -> dict[str, Any] | None:
        """Load the latest checkpoint for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        checkpoints = self._checkpoints.get(task_id, [])
        if not checkpoints:
            return None

        return checkpoints[-1]

    async def delete_checkpoint(self, task_id: UUID) -> None:
        """Delete checkpoint(s) for a task."""
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if task_id in self._checkpoints:
            del self._checkpoints[task_id]
            logger.debug(f"Deleted checkpoint(s) for task {task_id}")

    async def list_checkpoints(
        self, task_id: UUID | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List checkpoints, optionally filtered by task_id."""
        results = []

        for cp_task_id, checkpoints in self._checkpoints.items():
            if task_id is not None and cp_task_id != task_id:
                continue
            for cp in checkpoints:
                results.append(
                    {
                        "task_id": cp_task_id,
                        "checkpoint_data": cp.get("checkpoint_data", {}),
                        "step_number": cp.get("step_number", 0),
                        "step_label": cp.get("step_label"),
                        "created_at": cp.get("created_at"),
                    }
                )

        # Sort by created_at descending (most recent first)
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return results[:limit]
