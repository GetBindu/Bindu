"""In-memory scheduler implementation."""

from __future__ import annotations as _annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Any

import anyio
from opentelemetry.trace import get_current_span

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.server.scheduler.base import (
    Scheduler,
    TaskOperation,
    _CancelTask,
    _PauseTask,
    _ResumeTask,
    _RunTask,
)
from bindu.utils.logging import get_logger
from bindu.utils.retry import retry_scheduler_operation

logger = get_logger("bindu.server.scheduler.memory_scheduler")

# Constants
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_MIN_WAIT = 0.1
DEFAULT_RETRY_MAX_WAIT = 1.0

# Bounded buffer prevents unbounded memory growth while allowing the API
# handler to enqueue a task before the worker loop is ready to receive.
_TASK_QUEUE_BUFFER_SIZE = 100


class InMemoryScheduler(Scheduler):
    """A scheduler that schedules tasks in memory."""

    async def __aenter__(self):
        """Enter async context manager."""
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        # Bounded buffer allows the API handler to enqueue tasks before the
        # worker loop is ready while preventing unbounded memory growth.
        self._write_stream, self._read_stream = anyio.create_memory_object_stream[
            TaskOperation
        ](_TASK_QUEUE_BUFFER_SIZE)
        await self.aexit_stack.enter_async_context(self._read_stream)
        await self.aexit_stack.enter_async_context(self._write_stream)

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager."""
        await self.aexit_stack.__aexit__(exc_type, exc_value, traceback)

    async def _send_operation(
        self,
        operation_class: type,
        operation: str,
        params: TaskSendParams | TaskIdParams,
    ) -> None:
        """Send task operation with live span for trace context.

        Uses non-blocking send_nowait to fail fast when the buffer is full,
        preventing the API handler from hanging indefinitely.

        Args:
            operation_class: The operation class to instantiate
            operation: Operation type string
            params: Task parameters

        Raises:
            Exception: If the bounded buffer is full (task queue at capacity)
        """
        task_op = operation_class(
            operation=operation, params=params, _current_span=get_current_span()
        )
        try:
            # Use send_nowait for non-blocking behavior - fails fast if buffer is full
            self._write_stream.send_nowait(task_op)
        except anyio.WouldBlock:
            # Re-raise with a clear message indicating buffer/full condition
            raise RuntimeError(
                f"Task queue buffer full: could not schedule {operation} operation. "
                f"Maximum capacity ({_TASK_QUEUE_BUFFER_SIZE}) reached."
            )

    @retry_scheduler_operation(
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        min_wait=DEFAULT_RETRY_MIN_WAIT,
        max_wait=DEFAULT_RETRY_MAX_WAIT,
    )
    async def run_task(self, params: TaskSendParams) -> None:
        """Schedule a task for execution."""
        logger.debug(f"Running task: {params}")
        await self._send_operation(_RunTask, "run", params)

    @retry_scheduler_operation(
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        min_wait=DEFAULT_RETRY_MIN_WAIT,
        max_wait=DEFAULT_RETRY_MAX_WAIT,
    )
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a scheduled task."""
        logger.debug(f"Canceling task: {params}")
        await self._send_operation(_CancelTask, "cancel", params)

    @retry_scheduler_operation(
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        min_wait=DEFAULT_RETRY_MIN_WAIT,
        max_wait=DEFAULT_RETRY_MAX_WAIT,
    )
    async def pause_task(self, params: TaskIdParams) -> None:
        """Pause a running task."""
        logger.debug(f"Pausing task: {params}")
        await self._send_operation(_PauseTask, "pause", params)

    @retry_scheduler_operation(
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        min_wait=DEFAULT_RETRY_MIN_WAIT,
        max_wait=DEFAULT_RETRY_MAX_WAIT,
    )
    async def resume_task(self, params: TaskIdParams) -> None:
        """Resume a paused task."""
        logger.debug(f"Resuming task: {params}")
        await self._send_operation(_ResumeTask, "resume", params)

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the scheduler."""
        async for task_operation in self._read_stream:
            yield task_operation
