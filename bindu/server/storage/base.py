"""Base storage interface for task and context management."""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from typing import Any, Generic
from uuid import UUID

from typing_extensions import TypeVar

from bindu.common.protocol.types import (
    Artifact,
    Message,
    PushNotificationConfig,
    Task,
    TaskState,
)

ContextT = TypeVar("ContextT", default=dict[str, Any])


class OwnershipError(Exception):
    """Raised when a caller attempts to use a resource owned by someone else.

    Storage raises this to refuse a write (``submit_task`` against an existing
    context with a different owner). Handlers catch it and convert to a
    ``ContextNotFoundError`` / ``TaskNotFoundError`` JSON-RPC response so the
    error does not leak the existence of the resource to the caller.
    """


class Storage(ABC, Generic[ContextT]):
    """Abstract storage interface for A2A protocol task and context management.

    Responsibilities:
    - Task Lifecycle: Store, retrieve, and update tasks following A2A protocol
    - Context Management: Maintain conversation context across multiple tasks
    - History Tracking: Preserve message history and task artifacts

    Hybrid Agent Pattern Support:
    - Messages during execution: update_task(state="input-required", new_messages=[...])
    - Artifacts at completion: update_task(state="completed", new_artifacts=[...], new_messages=[...])
    - Context continuity: append_to_contexts() for incremental message history
    - Task refinements: list_tasks_by_context() to build conversation from related tasks

    Type Parameters:
        ContextT: Custom context type for agent-specific implementations
    """

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from storage.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise
        """

    @abstractmethod
    async def submit_task(
        self,
        context_id: UUID,
        message: Message,
        caller_did: str | None = None,
    ) -> Task:
        """Create and store a new task.

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request
            caller_did: Identity of the authenticated caller, recorded as the
                task's owner (and, if this call also creates the context, the
                context's owner). ``None`` is allowed for deployments with auth
                disabled.

        Returns:
            Newly created task in 'submitted' state

        Raises:
            OwnershipError: If ``context_id`` refers to an existing context
                whose ``owner_did`` does not match ``caller_did``. Callers
                must translate this to a ``ContextNotFoundError`` JSON-RPC
                response to avoid leaking the context's existence.
            ValueError: If the existing task is in a terminal state (immutable).
        """

    @abstractmethod
    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Update task state and append new content.

        Args:
            task_id: Task to update
            state: New task state (working, completed, failed, etc.)
            new_artifacts: Optional artifacts to append
            new_messages: Optional messages to append to history
            metadata: Optional metadata to update/merge with task metadata

        Returns:
            Updated task object
        """

    @abstractmethod
    async def list_tasks(
        self,
        length: int | None = None,
        offset: int = 0,
        owner_did: str | None = None,
    ) -> list[Task]:
        """List tasks in storage, optionally filtered by owner.

        Args:
            length: Optional limit on number of tasks to return (most recent)
            offset: Optional offset for pagination
            owner_did: When provided, only tasks with exactly this ``owner_did``
                are returned (WHERE owner_did = :owner_did). When ``None`` (the
                default), no owner filter is applied — rows are returned
                regardless of ownership. Public handlers must pass the
                authenticated caller's DID; internal callers (workers, metrics)
                leave this unset to retain today's unfiltered behavior. Note
                that ``owner_did=None`` does NOT mean "filter to NULL-owner
                rows"; it means "no filter at all," matching the convention
                used by :meth:`count_tasks`.

        Returns:
            List of tasks
        """

    @abstractmethod
    async def count_tasks(self, status: TaskState | None = None) -> int:
        """Count number of tasks, optionally filtered by status.

        Args:
            status: Optional strict TaskState to filter by (e.g. 'submitted', 'working')

        Returns:
            Count of matching tasks

        Note:
            Must be implemented by subclasses to ensure efficient DB-level counting
            (e.g., SELECT COUNT(*)) rather than loading all records into Python memory.
        """

    @abstractmethod
    async def list_tasks_by_context(
        self,
        context_id: UUID,
        length: int | None = None,
        offset: int = 0,
        owner_did: str | None = None,
    ) -> list[Task]:
        """List tasks belonging to a specific context.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return (most recent)
            offset: Optional offset for pagination
            owner_did: When provided, additionally filter to tasks owned by
                this DID. ``None`` means no owner filter. See
                :meth:`list_tasks` for the full semantics.

        Returns:
            List of tasks in the context
        """

    # -------------------------------------------------------------------------
    # Context Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def load_context(self, context_id: UUID) -> ContextT | None:
        """Load context from storage.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Context object if found, None otherwise
        """

    @abstractmethod
    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history.

        Efficient operation that updates context without full rebuild.

        Args:
            context_id: Context to update
            messages: Messages to append to history
        """

    @abstractmethod
    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context.

        Args:
            context_id: Context identifier
            context: Context data (format determined by agent implementation)
        """

    @abstractmethod
    async def list_contexts(
        self,
        length: int | None = None,
        offset: int = 0,
        owner_did: str | None = None,
    ) -> list[ContextT]:
        """List contexts in storage, optionally filtered by owner.

        Args:
            length: Optional limit on number of contexts to return (most recent)
            offset: Optional offset for pagination
            owner_did: When provided, only contexts with exactly this
                ``owner_did`` are returned. ``None`` means no owner filter.
                See :meth:`list_tasks` for the full semantics.

        Returns:
            List of strictly typed ContextT objects
        """

    # -------------------------------------------------------------------------
    # Utility & Lifecycle Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context.

        Args:
            context_id: The context ID to clear

        Warning: This is a destructive operation.
        """

    @abstractmethod
    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """

    @abstractmethod
    async def close(self) -> None:
        """Safely close database connection pools and cleanup resources.

        Ensures graceful shutdown for persistent storage engines.
        """

    # -------------------------------------------------------------------------
    # Feedback Operations (Optional)
    # -------------------------------------------------------------------------

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task.

        Optional operation - implementations may choose to store feedback
        as task metadata or in dedicated storage.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content (rating, comments, etc.)
        """
        pass

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists
        """
        return None

    # -------------------------------------------------------------------------
    # Webhook Persistence Operations (for long-running tasks)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def save_webhook_config(
        self, task_id: UUID, config: PushNotificationConfig
    ) -> None:
        """Save a webhook configuration for a task.

        Used to persist webhook configurations for long-running tasks
        that may outlive server restarts.

        Args:
            task_id: Task to associate the webhook config with
            config: Push notification configuration to persist
        """

    @abstractmethod
    async def load_webhook_config(self, task_id: UUID) -> PushNotificationConfig | None:
        """Load a webhook configuration for a task.

        Args:
            task_id: Task to load the webhook config for

        Returns:
            The webhook configuration if found, None otherwise
        """

    @abstractmethod
    async def delete_webhook_config(self, task_id: UUID) -> None:
        """Delete a webhook configuration for a task.

        Args:
            task_id: Task to delete the webhook config for

        Note: Should not raise if the config doesn't exist.
        """

    @abstractmethod
    async def load_all_webhook_configs(self) -> dict[UUID, PushNotificationConfig]:
        """Load all stored webhook configurations.

        Used during initialization to restore webhook state after restart.

        Returns:
            Dictionary mapping task IDs to their webhook configurations
        """

    # -------------------------------------------------------------------------
    # Ownership Lookup (for access-control enforcement)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_task_owner(self, task_id: UUID) -> str | None:
        """Return the ``owner_did`` for a task.

        Phase 2 handlers call this to compare the caller's identity against the
        task owner before returning or mutating the row. Returns ``None`` when
        the task does not exist OR when the task pre-dates ownership tracking
        (rows written before the ``owner_did`` column existed). Callers MUST
        treat "task exists but owner is None" as equivalent to "unowned" and
        decide policy at the handler layer — do not infer existence from this
        call.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Owner DID string if recorded, None otherwise
        """

    @abstractmethod
    async def get_context_owner(self, context_id: UUID) -> str | None:
        """Return the ``owner_did`` for a context.

        Semantics mirror :meth:`get_task_owner`. A context's owner is fixed on
        first write (``submit_task`` that creates the context) and never
        changes.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Owner DID string if recorded, None otherwise
        """
