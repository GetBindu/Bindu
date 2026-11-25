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
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, cast

import anyio
from opentelemetry.trace import get_tracer, use_span

from bindu.server.scheduler import TaskOperation

from bindu.common.protocol.types import Artifact, Message, TaskIdParams, TaskSendParams
from bindu.server.scheduler.base import Scheduler
from bindu.server.storage.base import Storage
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

tracer = get_tracer(__name__)
logger = get_logger(__name__)

# Bound on the shielded scheduler send during shutdown requeue: long enough
# for a healthy broker round-trip, short enough that a dead consumer can't
# wedge worker exit.
REQUEUE_SEND_TIMEOUT_SECONDS = 5.0


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

    max_concurrent_tasks: int = field(default=1, kw_only=True)
    """Maximum run operations this worker executes concurrently.

    Defaults to 1 — strict serial execution, identical to the historical
    behaviour. Regardless of this cap, run operations that share a
    context_id are always serialized in arrival order: agents with
    enable_context_based_history build their message list from the
    context's pre-turn history, so two same-context tasks running at once
    would read the same history and write over each other.
    """

    _run_semaphore: anyio.Semaphore | None = field(default=None, init=False, repr=False)
    """Caps concurrent run executions. Created when the worker starts."""

    _context_locks: dict[str, anyio.Lock] = field(
        default_factory=dict, init=False, repr=False
    )
    """Per-context_id locks serializing same-context runs in arrival order."""

    _context_lock_refs: dict[str, int] = field(
        default_factory=dict, init=False, repr=False
    )
    """Holder/waiter counts for _context_locks so idle locks are dropped."""

    _in_flight_scopes: dict[Any, anyio.CancelScope] = field(
        default_factory=dict, init=False, repr=False
    )
    """Cancel scope per executing task_id, so cancel_task can interrupt the run."""

    # -------------------------------------------------------------------------
    # Worker Lifecycle
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Start the worker and begin processing tasks.

        Context manager that:
        1. Starts the worker loop in a task group
        2. Yields control to caller
        3. Cancels worker on exit (in-flight runs are marked canceled, not
           stranded in 'working' — see _finalize_interrupted_task)

        Usage:
            async with worker.run():
                # Worker is running
                ...
            # Worker stopped
        """
        self._run_semaphore = anyio.Semaphore(max(1, self.max_concurrent_tasks))
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        """Dispatch task operations as they arrive.

        Run operations are spawned into a task group — gated by the
        concurrency cap and a per-context lock — instead of being awaited
        inline, so one slow task cannot stall every task queued behind it.
        Control operations (cancel/pause/resume) are spawned ungated: a
        cancel must never wait behind the run it is trying to stop, which
        also requires this loop to keep draining the scheduler stream
        eagerly. The semaphore in _run_task_operation, not this loop or
        the scheduler buffer, is what bounds concurrent provider spend.
        """
        async with anyio.create_task_group() as tg:
            async for task_operation in self.scheduler.receive_task_operations():
                if task_operation["operation"] == "run":
                    tg.start_soon(self._run_task_operation, task_operation)
                else:
                    tg.start_soon(self._control_task_operation, task_operation)

    async def _run_task_operation(self, task_operation: TaskOperation) -> None:
        """Execute one run operation under the worker's concurrency gates.

        Gate order matters: the context lock is taken before the semaphore
        so a same-context task waiting its turn does not occupy one of the
        max_concurrent_tasks slots while it blocks.

        Each spawned operation keeps its own failure guard — the task group
        would otherwise cancel every sibling (and the dispatch loop) when
        one operation raises.
        """
        params = task_operation["params"]
        task_id = self._normalize_uuid(params["task_id"])
        context_key = str(params.get("context_id") or task_id)
        run_started = False
        try:
            async with self._context_guard(context_key):
                assert self._run_semaphore is not None, "worker not started via run()"
                async with self._run_semaphore:
                    with anyio.CancelScope() as cancel_scope:
                        self._in_flight_scopes[task_id] = cancel_scope
                        run_started = True
                        try:
                            await self._handle_task_operation(task_operation)
                        finally:
                            self._in_flight_scopes.pop(task_id, None)
                    if cancel_scope.cancelled_caught:
                        # tasks/cancel interrupted this run mid-flight. The
                        # cancel handler records the canceled state; this is
                        # a backstop for the write racing the interruption.
                        logger.info(f"Task {task_id} run interrupted by cancel")
                        await self._finalize_interrupted_task(task_id)
        except anyio.get_cancelled_exc_class():
            # Worker shutdown.
            with anyio.CancelScope(shield=True):
                if run_started:
                    # Mid-run: side effects may have happened, so re-running
                    # is not safe — don't strand it in 'working'.
                    await self._finalize_interrupted_task(task_id)
                else:
                    # Still waiting on the concurrency gates: eager dispatch
                    # already consumed the operation from the scheduler, so
                    # hand it back for a restarted worker to run.
                    await self._requeue_task_operation(task_operation)
            raise
        except Exception as e:  # noqa: BLE001 - last-resort guard so no operation can kill the dispatch loop
            logger.error(
                f"Unhandled error dispatching task {task_id}: {e}", exc_info=True
            )

    async def _control_task_operation(self, task_operation: TaskOperation) -> None:
        """Execute a control operation (cancel/pause/resume) immediately."""
        try:
            await self._handle_task_operation(task_operation)
        except Exception as e:  # noqa: BLE001 - last-resort guard so no operation can kill the dispatch loop
            logger.error(
                f"Unhandled error in {task_operation['operation']} operation: {e}",
                exc_info=True,
            )

    @asynccontextmanager
    async def _context_guard(self, context_key: str) -> AsyncIterator[None]:
        """Serialize run operations sharing a context_id, in arrival order.

        Locks are created on demand and dropped once no task holds or
        waits on them, so the map does not grow with context cardinality.
        """
        lock = self._context_locks.get(context_key)
        if lock is None:
            lock = anyio.Lock()
            self._context_locks[context_key] = lock
        self._context_lock_refs[context_key] = (
            self._context_lock_refs.get(context_key, 0) + 1
        )
        try:
            async with lock:
                yield
        finally:
            remaining = self._context_lock_refs[context_key] - 1
            if remaining:
                self._context_lock_refs[context_key] = remaining
            else:
                del self._context_lock_refs[context_key]
                self._context_locks.pop(context_key, None)

    def _cancel_in_flight(self, task_id: Any) -> bool:
        """Cancel the in-flight run for task_id, if one is executing.

        Returns:
            True if a running execution was found and its scope cancelled.
        """
        scope = self._in_flight_scopes.get(self._normalize_uuid(task_id))
        if scope is None:
            return False
        scope.cancel()
        return True

    async def _finalize_interrupted_task(self, task_id: Any) -> None:
        """Move an interrupted task out of non-terminal states.

        Uses the storage CAS so a task that already reached a terminal
        state (completed/failed/canceled) is never overwritten. Best-effort:
        on the shutdown path storage may already be closing.
        """
        try:
            for from_state in ("working", "submitted"):
                if await self.storage.update_task_state_if(
                    self._normalize_uuid(task_id), from_state, "canceled"
                ):
                    logger.info(
                        f"Task {task_id} interrupted while {from_state}; marked canceled"
                    )
                    return
        except Exception as e:  # noqa: BLE001 - best-effort cleanup during interruption/shutdown
            logger.warning(f"Could not finalize interrupted task {task_id}: {e}")

    async def _requeue_task_operation(self, task_operation: TaskOperation) -> None:
        """Return an un-started run operation to the scheduler on shutdown.

        Eager dispatch pops operations off the scheduler queue before a
        concurrency slot is free, so a graceful shutdown would otherwise
        consume queued work without ever running it. Requeueing keeps the
        task 'submitted' with its operation back on the queue (durable for
        Redis). Best-effort: when the scheduler no longer accepts sends,
        fall back to finalizing the task as canceled so it is never left
        'submitted' with its operation silently lost.
        """
        task_id = task_operation["params"]["task_id"]
        try:
            # Only run operations reach this method (_run_task_operation),
            # so the params are TaskSendParams by construction. The send is
            # bounded: it runs under the shutdown shield, and an in-memory
            # stream whose consumer (this worker's loop) is already gone
            # can fill up and would otherwise block the shielded send
            # forever, wedging worker exit. A timeout lands in the fallback
            # below instead.
            with anyio.fail_after(REQUEUE_SEND_TIMEOUT_SECONDS):
                await self.scheduler.run_task(
                    cast("TaskSendParams", task_operation["params"])
                )
            logger.info(f"Task {task_id} requeued; worker shut down before it started")
        except Exception as e:  # noqa: BLE001 - best-effort during shutdown
            logger.warning(f"Could not requeue task {task_id} on shutdown: {e}")
            await self._finalize_interrupted_task(task_id)

    async def _handle_task_operation(self, task_operation: TaskOperation) -> None:
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
            # Preserve trace context from scheduler (if available)
            span = task_operation.get("_current_span")
            ctx_manager = use_span(span) if span else nullcontext()
            with ctx_manager:
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
        except Exception as e:  # noqa: BLE001 - intentionally broad: any unhandled worker failure must mark the task as failed
            # Update task status to failed on any exception — guarded so a
            # state another writer already made terminal (e.g. an API cancel
            # racing this failure) is never overwritten.
            task_id = self._normalize_uuid(task_operation["params"]["task_id"])
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            updated = await self.storage.update_task(
                task_id,
                state="failed",
                expected_states=app_settings.agent.non_terminal_states,
            )
            if updated is None:
                logger.debug(
                    f"Task {task_id} already terminal; failure state not recorded"
                )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_uuid(value: Any) -> Any:
        """Normalize UUID value from string or UUID object.

        Args:
            value: UUID value (string, UUID object, or other)

        Returns:
            UUID object if input is string or UUID, otherwise returns input as-is
        """
        from uuid import UUID

        if isinstance(value, str):
            return UUID(value)
        return value

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
        """Prepare A2A protocol messages for agent execution.

        Args:
            history: List of protocol Message objects

        Returns:
            List in the format handlers consume. ManifestWorker passes A2A
            messages through with ``parts`` intact (the handler contract);
            chat-format flattening happens only at wire boundaries that
            require it (e.g. the gRPC proto).

        Example:
            Protocol: [{"role": "user", "parts": [{"kind": "text", "text": "Hello"}]}]
            Agent:    [{"role": "user", "parts": [{"kind": "text", "text": "Hello"}]}]
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

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Handle pause operation.

        TODO: Implement task pause functionality
        - Save current execution state
        - Update task to 'suspended' state
        - Release resources while preserving context
        """
        raise NotImplementedError("Pause operation not yet implemented")

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Handle resume operation.

        TODO: Implement task resume functionality
        - Restore execution state
        - Update task to 'resumed' state
        - Continue from last checkpoint
        """
        raise NotImplementedError("Resume operation not yet implemented")
