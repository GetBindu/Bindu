"""In-memory scheduler implementation."""

from __future__ import annotations as _annotations

import math
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


def _get_trace_context() -> tuple[str | None, str | None]:
    """Extract primitive trace context from the live OpenTelemetry span."""
    try:
        span = get_current_span()
        if span and hasattr(span, "get_span_context"):
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        pass
    return None, None


class InMemoryScheduler(Scheduler):
    """A scheduler that schedules tasks in memory."""

    async def __aenter__(self):
        """Enter async context manager."""
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        # FIX: Added math.inf to create a buffered stream.
        # Without this, the stream defaults to 0 (unbuffered), which causes
        # the API server to deadlock/hang waiting for a worker to receive the task.
        self._write_stream, self._read_stream = anyio.create_memory_object_stream[
            TaskOperation
        ](math.inf)
        await self.aexit_stack.enter_async_context(self._read_stream)
        await self.aexit_stack.enter_async_context(self._write_stream)

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager."""
        await self.aexit_stack.__aexit__(exc_type, exc_value, traceback)

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def run_task(self, params: TaskSendParams) -> None:
        """Schedule a task for execution."""
        logger.debug(f"Running task: {params}")
        trace_id, span_id = _get_trace_context()
        await self._write_stream.send(
            _RunTask(operation="run", params=params, trace_id=trace_id, span_id=span_id)
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a scheduled task."""
        logger.debug(f"Canceling task: {params}")
        trace_id, span_id = _get_trace_context()
        await self._write_stream.send(
            _CancelTask(
                operation="cancel", params=params, trace_id=trace_id, span_id=span_id
            )
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def pause_task(self, params: TaskIdParams) -> None:
        """Pause a running task."""
        logger.debug(f"Pausing task: {params}")
        trace_id, span_id = _get_trace_context()
        await self._write_stream.send(
            _PauseTask(
                operation="pause", params=params, trace_id=trace_id, span_id=span_id
            )
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def resume_task(self, params: TaskIdParams) -> None:
        """Resume a paused task."""
        logger.debug(f"Resuming task: {params}")
        trace_id, span_id = _get_trace_context()
        await self._write_stream.send(
            _ResumeTask(
                operation="resume", params=params, trace_id=trace_id, span_id=span_id
            )
        )

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the scheduler."""
        async for task_operation in self._read_stream:
            yield task_operation
