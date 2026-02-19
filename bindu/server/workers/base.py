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

    _running_tasks: dict[UUID, asyncio.Task[None]] = field(
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
        
        ALL operations are now processed in background tasks to ensure the loop
        never blocks. This allows pause/cancel operations to execute immediately
        even while long-running tasks are executing.
        """
        async for task_operation in self.scheduler.receive_task_operations():
            # Process ALL operations in background to keep loop responsive
            asyncio.create_task(self._handle_task_operation(task_operation))

    async def _handle_task_operation(self, task_operation: dict[str, Any]) -> None:
        """Dispatch task operation to appropriate handler.

        Args:
            task_operation: Operation dict with 'operation', 'params', and '_current_span'

        Supported Operations:
        - run: Execute a task (tracked in _running_tasks)
        - cancel: Cancel a running task
        - pause: Pause task execution (cancels task, saves checkpoint)
        - resume: Resume paused task (restores checkpoint, re-executes)

        Error Handling:
        - Any exception during execution marks task as 'failed'
        - Preserves OpenTelemetry trace context
        - CancelledError is caught and logged (not treated as failure)
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
        except asyncio.CancelledError:
            # Task was cancelled (pause/cancel operation) - this is expected
            logger.info(f"Task operation {task_operation['operation']} was cancelled")
            raise
        except Exception as e:
            # Update task status to failed on any exception
            from uuid import UUID

            task_id_raw = task_operation["params"]["task_id"]
            task_id = UUID(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self.storage.update_task(task_id, state="failed")

    async def _execute_and_track_task(self, params: TaskSendParams) -> None:
        """Execute task and track it in _running_tasks for pause/cancel support.

        Wraps run_task to enable execution control:
        - Registers task in _running_tasks before execution
        - Cleans up from _running_tasks after completion
        - Handles cancellation gracefully

        Args:
            params: Task execution parameters
        """
        task_id = params["task_id"]

        # Create task for execution
        task = asyncio.create_task(self.run_task(params))
        self._running_tasks[task_id] = task

        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} execution was cancelled")
            raise
        finally:
            # Always clean up tracking
            self._running_tasks.pop(task_id, None)

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
    # Pause/Resume Operations
    # -------------------------------------------------------------------------

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Pause a running task by cancelling execution and saving checkpoint.

        Execution Control Flow:
        1. Validate task exists and is in pausable state
        2. Cancel the running asyncio task if exists
        3. Save checkpoint to task metadata for resume
        4. Transition task to 'suspended' state

        Pausable States:
        - working: Task is actively executing
        - input-required: Task is waiting for user input
        - auth-required: Task is waiting for authentication

        Checkpoint Data:
        - state: Previous state before pause
        - paused_at: ISO timestamp when paused
        - history_length: Number of messages at pause time

        Args:
            params: Task identifier parameters

        Raises:
            ValueError: If task not found or in non-pausable state
        """
        task_id = params["task_id"]
        
        # CRITICAL: Cancel running task FIRST before loading from storage
        # If we wait to load the task, it might complete before we can cancel it
        running_task = self._running_tasks.get(task_id)
        if running_task and not running_task.done():
            logger.info(f"Cancelling running task {task_id} for pause operation")
            running_task.cancel()
            try:
                # Wait briefly for cancellation to complete
                await asyncio.wait_for(running_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                # Expected - task was cancelled or took too long
                logger.debug(f"Task {task_id} cancellation completed")
                pass
            finally:
                self._running_tasks.pop(task_id, None)
        
        # Now load task and validate state
        task = await self.storage.load_task(task_id)

        if task is None:
            raise ValueError(f"Task {task_id} not found")

        current_state = task["status"]["state"]
        pausable_states = {"working", "input-required", "auth-required"}

        if current_state not in pausable_states:
            pausable_list = ", ".join(sorted(pausable_states))
            raise ValueError(
                f"Cannot pause task in state '{current_state}'. "
                f"Task must be in one of: {pausable_list}"
            )

        # Create checkpoint data
        from datetime import datetime, timezone

        checkpoint = {
            "state": current_state,
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "history_length": len(task.get("history", [])),
        }

        # Add span event for pause operation
        from opentelemetry.trace import get_current_span

        current_span = get_current_span()
        if current_span.is_recording():
            current_span.add_event(
                "task.paused",
                attributes={
                    "task_id": str(task_id),
                    "previous_state": current_state,
                    "checkpoint_saved": True,
                },
            )

        # Transition to paused with checkpoint
        existing_metadata = task.get("metadata", {})
        updated_metadata = {**existing_metadata, "checkpoint": checkpoint}
        await self.storage.update_task(
            task_id, state="paused", metadata=updated_metadata
        )
        logger.info(
            f"Task {task_id} paused and checkpoint saved (was {current_state})"
        )

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Resume a paused task by restoring checkpoint and re-queueing.

        Execution Control Flow:
        1. Validate task is in 'paused' state
        2. Load checkpoint from task metadata
        3. Restore previous state from checkpoint
        4. Re-queue task for execution

        The resumed task will be picked up by the scheduler and executed
        from its previous state. The checkpoint is preserved in metadata
        for debugging/audit purposes.

        Args:
            params: Task identifier parameters

        Raises:
            ValueError: If task not found, not paused, or missing checkpoint
        """
        task_id = params["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            raise ValueError(f"Task {task_id} not found")

        current_state = task["status"]["state"]

        if current_state != "paused":
            raise ValueError(
                f"Cannot resume task in state '{current_state}'. "
                f"Task must be in 'paused' state"
            )

        # Load checkpoint
        metadata = task.get("metadata", {})
        checkpoint = metadata.get("checkpoint")

        if not checkpoint:
            logger.warning(
                f"Task {task_id} missing checkpoint, resuming as 'working'"
            )
            restored_state = "working"
        else:
            restored_state = checkpoint.get("state", "working")
            logger.info(
                f"Task {task_id} restoring checkpoint from {checkpoint.get('paused_at')}"
            )

        # Add span event for resume operation
        from opentelemetry.trace import get_current_span

        current_span = get_current_span()
        if current_span.is_recording():
            current_span.add_event(
                "task.resumed",
                attributes={
                    "task_id": str(task_id),
                    "restored_state": restored_state,
                    "checkpoint_restored": checkpoint is not None,
                },
            )

        # Transition to restored state (working/input-required/auth-required)
        await self.storage.update_task(task_id, state=restored_state)
        logger.info(f"Task {task_id} resumed to state '{restored_state}'")
