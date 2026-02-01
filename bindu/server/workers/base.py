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

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

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
            await self._handle_task_operation(task_operation)

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
            "run": self.run_task,
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
    # Pause/Resume Operations
    # -------------------------------------------------------------------------

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Handle pause operation.

        Pauses a task by transitioning it to 'suspended' state.
        The task can be resumed later from where it was paused.

        Valid Source States:
        - working: Task is actively executing
        - input-required: Task is waiting for user input
        - auth-required: Task is waiting for authentication

        Invalid Source States:
        - submitted: Task hasn't started yet (no execution to pause)
        - completed, failed, canceled: Terminal states (cannot be paused)
        - suspended: Already paused
        - resumed: Transient state during resumption

        Args:
            params: Task identification parameters containing task_id

        Raises:
            ValueError: If task not found or in invalid state for pausing
        """
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(f"Task {params['task_id']} not found")

        current_state = task["status"]["state"]
        pausable_states = {"working", "input-required", "auth-required"}

        if current_state not in pausable_states:
            raise ValueError(
                f"Cannot pause task in state '{current_state}'. "
                f"Task must be in one of: {pausable_states}"
            )

        # Add span event for state transition
        from opentelemetry.trace import get_current_span

        current_span = get_current_span()
        if current_span.is_recording():
            current_span.add_event(
                "task.state_changed",
                attributes={
                    "from_state": current_state,
                    "to_state": "suspended",
                    "operation": "pause",
                },
            )

        # Transition to suspended state
        # Task context and history are preserved in storage
        await self.storage.update_task(params["task_id"], state="suspended")
        logger.info(f"Task {params['task_id']} paused from state '{current_state}'")

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Handle resume operation.

        Resumes a suspended task by transitioning it to 'resumed' state,
        which will trigger re-execution from its last known state.

        Valid Source State:
        - suspended: Task was previously paused

        Invalid Source States:
        - working, input-required, auth-required: Already active
        - completed, failed, canceled: Terminal states (cannot be resumed)
        - submitted: Never started (use run_task instead)
        - resumed: Already resumed

        Args:
            params: Task identification parameters containing task_id

        Raises:
            ValueError: If task not found or not in suspended state

        Note:
            After resuming, the worker should re-execute the task using run_task
            with the preserved context and history. The 'resumed' state is transient
            and will transition to 'working' upon re-execution.
        """
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(f"Task {params['task_id']} not found")

        current_state = task["status"]["state"]

        if current_state != "suspended":
            raise ValueError(
                f"Cannot resume task in state '{current_state}'. "
                f"Task must be in 'suspended' state."
            )

        # Add span event for state transition
        from opentelemetry.trace import get_current_span

        current_span = get_current_span()
        if current_span.is_recording():
            current_span.add_event(
                "task.state_changed",
                attributes={
                    "from_state": "suspended",
                    "to_state": "resumed",
                    "operation": "resume",
                },
            )

        # Transition to resumed state
        # The task will be re-executed by the worker with preserved context
        await self.storage.update_task(params["task_id"], state="resumed")
        logger.info(f"Task {params['task_id']} resumed and ready for re-execution")
