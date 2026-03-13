"""Base scheduler module."""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import Discriminator
from typing_extensions import Self, TypedDict

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.scheduler.base")


class Scheduler(ABC):
    """The scheduler class is in charge of scheduling the tasks."""

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Send a task to be executed by the worker."""

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a task."""

    @abstractmethod
    async def pause_task(self, params: TaskIdParams) -> None:
        """Pause a task."""

    @abstractmethod
    async def resume_task(self, params: TaskIdParams) -> None:
        """Resume a task."""

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager."""
        ...

    @abstractmethod
    def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the broker.

        On a multi-worker setup, the broker will need to round-robin the task operations
        between the workers.
        """


OperationT = TypeVar("OperationT")
ParamsT = TypeVar("ParamsT")


class _TaskOperation(TypedDict, Generic[OperationT, ParamsT]):
    """A task operation.

    Refactored to use primitive trace_id/span_id instead of a live OpenTelemetry
    Span object to support distributed JSON serialization safely.
    """

    operation: OperationT
    params: ParamsT
    trace_id: str | None
    span_id: str | None


_RunTask = _TaskOperation[Literal["run"], TaskSendParams]
_CancelTask = _TaskOperation[Literal["cancel"], TaskIdParams]
_PauseTask = _TaskOperation[Literal["pause"], TaskIdParams]
_ResumeTask = _TaskOperation[Literal["resume"], TaskIdParams]

TaskOperation = Annotated[
    "_RunTask | _CancelTask | _PauseTask | _ResumeTask", Discriminator("operation")
]
