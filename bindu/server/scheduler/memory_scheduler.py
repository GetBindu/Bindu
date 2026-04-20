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


class InMemoryScheduler(Scheduler):
    """A scheduler that schedules tasks in memory."""

    async def __aenter__(self):
        """Enter async context manager."""
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        # Buffer of 100 prevents deadlock: without buffering the sender blocks
        # until a worker is ready to receive, which stalls the API server.
        # math.inf was previously used here but removed to restore backpressure.
        self._write_stream, self._read_stream = anyio.create_memory_object_stream[
            TaskOperation
        ](100)
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

        Args:
            operation_class: The operation class to instantiate
            operation: Operation type string
            params: Task parameters
        """
        task_op = operation_class(
            operation=operation, params=params, _current_span=get_current_span()
        )
        await self._write_stream.send(task_op)

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
