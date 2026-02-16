"""Base worker implementation for A2A protocol task execution.

Workers are the execution engines that process tasks from the scheduler.
They bridge the gap between the A2A protocol and actual agent implementation,
handling task lifecycle, error recovery, and observability.

Architecture:
- Workers receive task operations from the Scheduler
- Execute tasks using agent-specific logic (ManifestWorker, etc.)
- Update task state in Storage
- Handle errors and state transitions
- Provide observability through OpenTelemetry tracing

Hybrid Agent Pattern:
Workers implement the hybrid pattern by:
- Processing tasks through multiple state transitions
- Supporting input-required and auth-required states
- Generating artifacts only on task completion
"""

from __future__ import annotations as _annotations

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from uuid import UUID
from datetime import datetime, timezone

import anyio
from opentelemetry.trace import get_tracer, use_span

from bindu.common.protocol.types import Artifact, Message, TaskIdParams, TaskSendParams
from bindu.server.scheduler.base import Scheduler
from bindu.server.storage.base import Storage
from bindu.utils.logging import get_logger

tracer = get_tracer(__name__)
logger = get_logger(__name__)


@dataclass
class Worker(ABC):
    """Abstract base worker for A2A protocol task execution.

    Responsibilities:
    - Task Execution: Process tasks received from scheduler
    - State Management: Update task states through lifecycle
    - Error Handling: Gracefully handle failures and update task status
    - Observability: Trace task operations with OpenTelemetry

    Lifecycle:
    1. Worker starts and connects to scheduler
    2. Receives task operations (run, cancel, pause, resume)
    3. Executes operations with proper error handling
    4. Updates task state in storage
    5. Provides tracing for monitoring

    Subclasses must implement:
    - run_task(): Execute task logic
    - cancel_task(): Handle task cancellation
    - build_message_history(): Convert protocol messages to execution format
    - build_artifacts(): Convert results to protocol artifacts
    """

    scheduler: Scheduler
    """Scheduler that provides task operations to execute."""

    storage: Storage[Any]
    """Storage backend for task and context persistence."""

    _running_tasks: dict[UUID, anyio.CancelScope] = field(
        default_factory=dict, init=False, repr=False
    )
    """Active task executions mapped by task_id for pause/cancel control."""

    # -------------------------------------------------------------------------
    # Worker Lifecycle
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Start the worker and begin processing tasks.

        Context manager that:
        1. Starts the worker loop in a task group
        2. Yields control to caller
        3. Cancels worker on exit

        Usage:
            async with worker.run():
                # Worker is running
                ...
            # Worker stopped
        """
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        """Process task operations continuously.

        Receives task operations from scheduler and dispatches them to handlers.
        Runs until cancelled by the task group.
        """
        async for task_operation in self.scheduler.receive_task_operations():
            asyncio.create_task(self._handle_task_operation(task_operation))

    async def _handle_task_operation(self, task_operation: dict[str, Any]) -> None:
        """Dispatch task operation to appropriate handler.

        Args:
            task_operation: Operation dict with 'operation', 'params', and '_current_span'

        Supported Operations:
        - run: Execute a task
        - cancel: Cancel a running task
        - pause: Pause task execution (future)
        - resume: Resume paused task (future)

        Error Handling:
        - Any exception during execution marks task as 'failed'
        - Preserves OpenTelemetry trace context
        """
        operation_handlers: dict[str, Any] = {
            "run": self._execute_and_track_task,
            "cancel": self.cancel_task,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
        }

        try:
            # Preserve trace context from scheduler
            with use_span(task_operation["_current_span"]):
                with tracer.start_as_current_span(
                    f"{task_operation['operation']} task",
                    attributes={"logfire.tags": ["bindu"]},
                ):
                    handler = operation_handlers.get(task_operation["operation"])
                    if handler:
                        await handler(task_operation["params"])
                    else:
                        logger.warning(
                            f"Unknown operation: {task_operation['operation']}"
                        )
        except Exception as e:
            # Update task status to failed on any exception
            from uuid import UUID

            task_id_raw = task_operation["params"]["task_id"]
            task_id = UUID(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self.storage.update_task(task_id, state="failed")

    # -------------------------------------------------------------------------
    # Abstract Methods (Must Implement)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task with given parameters.

        Args:
            params: Task execution parameters including task_id, context_id, message

        Implementation should:
        1. Load task from storage
        2. Build message history from context
        3. Execute agent logic
        4. Handle state transitions (working → input-required → completed)
        5. Generate artifacts on completion
        6. Update storage with results
        """
        ...

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters

        Implementation should:
        1. Stop task execution if running
        2. Update task state to 'canceled'
        3. Clean up any resources
        """
        ...

    @abstractmethod
    def build_message_history(self, history: list[Message]) -> list[Any]:
        """Convert A2A protocol messages to agent-specific format.

        Args:
            history: List of protocol Message objects

        Returns:
            List in format suitable for agent execution (e.g., chat format for LLMs)

        Example:
            Protocol: [{"role": "user", "parts": [{"text": "Hello"}]}]
            Agent: [{"role": "user", "content": "Hello"}]
        """
        ...

    @abstractmethod
    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert agent execution result to A2A protocol artifacts.

        Args:
            result: Agent execution result (any format)

        Returns:
            List of Artifact objects with proper structure

        Hybrid Pattern:
        - Only called when task completes successfully
        - Artifacts represent final deliverable
        - Must include artifact_id, parts, and optional metadata
        """
        ...

    # -------------------------------------------------------------------------
    # Future Operations (Not Yet Implemented)
    # -------------------------------------------------------------------------

    async def _execute_and_track_task(self, params: TaskSendParams) -> None:
        """Execute task and track it in _running_tasks for pause/cancel support.

        Args:
            params: Task execution parameters
        """
        task_id_raw = params["task_id"]
        task_id = UUID(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw

        current_task = asyncio.current_task()
        if current_task:
            self._running_tasks[task_id] = current_task

        try:
            await self.run_task(params)
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} execution was cancelled")
            raise
        finally:
            self._running_tasks.pop(task_id, None)

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Handle pause operation.

        Pauses a running task by canceling execution and updating state.
        Does NOT compress history - keeps it accessible.
        """
        task_id_raw = params["task_id"]
        task_id = UUID(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw

        # 1. Cancel running task FIRST
        running_task = self._running_tasks.get(task_id)
        if running_task and not running_task.done():
            logger.info(f"Cancelling running task {task_id} for pause operation")
            running_task.cancel()
            try:
                import asyncio

                await asyncio.wait_for(running_task, timeout=2.0)
            except Exception:
                pass

        # 2. Load task to validate state
        task = await self.storage.load_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        current_state = task["status"]["state"]

        # 3. Create snapshot state (metadata only)
        state_snapshot = {
            "previous_state": current_state,
            "paused_at": datetime.now(timezone.utc).isoformat(),
        }

        # 4. Update task metadata and state
        # We store subtasks if they exist in the running state, but here we assume
        # subtasks are stored in the DB as separate entities or in the 'subtasks' field if supported.
        # For now, we just mark the main task as paused.
        # If the worker supports subtasks, it should have updated them.

        await self.storage.update_task(
            task_id, state="paused", metadata={"pause_snapshot": state_snapshot}
        )

        # Add span event
        current_span = get_tracer(__name__).start_span("task.paused")
        current_span.set_attribute("task_id", str(task_id))
        current_span.end()

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Handle resume operation.

        Resumes a paused task by restoring its state from metadata.
        """
        task_id_raw = params["task_id"]
        task_id = UUID(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw

        task = await self.storage.load_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        if task["status"]["state"] != "paused":
            raise ValueError(f"Task {task_id} is not paused")

        # Load snapshot
        metadata = task.get("metadata", {})
        snapshot = metadata.get("pause_snapshot", {})
        restored_state = snapshot.get("previous_state", "working")

        # Update state to restored state
        await self.storage.update_task(task_id, state=restored_state)

        logger.info(f"Task {task_id} resumed to state '{restored_state}'")
