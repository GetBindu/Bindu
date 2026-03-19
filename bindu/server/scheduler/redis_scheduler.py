"""Redis scheduler implementation for distributed task scheduling."""

from __future__ import annotations as _annotations

import json
import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from opentelemetry.trace import get_current_span

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.utils.logging import get_logger
from bindu.utils.retry import retry_scheduler_operation

from .base import (
    Scheduler,
    TaskOperation,
    _CancelTask,
    _PauseTask,
    _ResumeTask,
    _RunTask,
)

logger = get_logger("bindu.server.scheduler.redis_scheduler")


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


class RedisScheduler(Scheduler):
    """A Redis-based scheduler for distributed task operations."""

    def __init__(
        self,
        redis_url: str,
        queue_name: str = "bindu:tasks",
        max_connections: int = 10,
        retry_on_timeout: bool = True,
        poll_timeout: int = 1,
    ):
        """Initialize the Redis scheduler.

        Args:
            redis_url: Redis connection URL
            queue_name: Name of the Redis queue for task operations
            max_connections: Maximum number of Redis connections in the pool
            retry_on_timeout: Whether to retry operations on timeout
            poll_timeout: Timeout in seconds for blocking pop operations
        """
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.poll_timeout = poll_timeout
        self._redis_client: redis.Redis | None = None

    async def __aenter__(self):
        """Enter async context manager and initialize Redis connection."""
        self._redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=self.max_connections,
            retry_on_timeout=self.retry_on_timeout,
        )
        try:
            await self._redis_client.ping()
            logger.info(f"Redis scheduler connected to {self.redis_url}")
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(
                f"Unable to connect to Redis at {self.redis_url}: {e}"
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager and close Redis connection."""
        if self._redis_client:
            await self._redis_client.aclose()
            logger.info("Redis scheduler connection closed")
            self._redis_client = None

    @retry_scheduler_operation()
    async def run_task(self, params: TaskSendParams) -> None:
        """Schedule a task to run.

        Args:
            params: Parameters for the task to run
        """
        logger.debug(f"Scheduling run task: {params}")
        trace_id, span_id = _get_trace_context()
        task_operation = _RunTask(
            operation="run", params=params, trace_id=trace_id, span_id=span_id
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation()
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Schedule a task to be cancelled.

        Args:
            params: Parameters identifying the task to cancel
        """
        logger.debug(f"Scheduling cancel task: {params}")
        trace_id, span_id = _get_trace_context()
        task_operation = _CancelTask(
            operation="cancel", params=params, trace_id=trace_id, span_id=span_id
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation()
    async def pause_task(self, params: TaskIdParams) -> None:
        """Schedule a task to be paused.

        Args:
            params: Parameters identifying the task to pause
        """
        logger.debug(f"Scheduling pause task: {params}")
        trace_id, span_id = _get_trace_context()
        task_operation = _PauseTask(
            operation="pause", params=params, trace_id=trace_id, span_id=span_id
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation()
    async def resume_task(self, params: TaskIdParams) -> None:
        """Schedule a task to be resumed.

        Args:
            params: Parameters identifying the task to resume
        """
        logger.debug(f"Scheduling resume task: {params}")
        trace_id, span_id = _get_trace_context()
        task_operation = _ResumeTask(
            operation="resume", params=params, trace_id=trace_id, span_id=span_id
        )
        await self._push_task_operation(task_operation)

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the Redis queue.

        Yields:
            TaskOperation: Task operations from the queue

        Raises:
            RuntimeError: If Redis client is not initialized
        """
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        logger.info(
            f"Starting to receive task operations from queue: {self.queue_name}"
        )

        while True:
            try:
                result = await self._redis_client.blpop(
                    self.queue_name, timeout=self.poll_timeout
                )

                if result:
                    _, task_data = result
                    task_operation = self._deserialize_task_operation(task_data)
                    logger.debug(
                        f"Received task operation: {task_operation['operation']}"
                    )
                    yield task_operation

            except redis.RedisError as e:
                logger.error(f"Redis error in receive_task_operations: {e}")
                # FIX: Prevent infinite tight-loop CPU burn if Redis disconnects
                await asyncio.sleep(1)
                continue
            except json.JSONDecodeError as e:
                logger.error(f"Failed to deserialize task operation: {e}")
                continue
            except (RuntimeError, AttributeError) as e:
                logger.error(f"Unexpected error in receive_task_operations: {e}")
                continue

    async def _push_task_operation(self, task_operation: TaskOperation) -> None:
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        try:
            serialized_task = self._serialize_task_operation(task_operation)
            await self._redis_client.rpush(self.queue_name, serialized_task)
            logger.debug(
                f"Pushed task operation to queue: {task_operation['operation']}"
            )
        except redis.RedisError as e:
            logger.error(f"Failed to push task operation to Redis: {e}")
            raise
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize task operation: {e}")
            raise

    def _serialize_task_operation(self, task_operation: TaskOperation) -> str:
        """Serialize task operation to JSON string.

        Optimized by utilizing the standard library's default string conversion
        for UUIDs, completely eliminating the slow manual recursive dictionary parsing.
        """
        return json.dumps(task_operation, default=str)

    def _deserialize_task_operation(self, task_data: str) -> TaskOperation:
        """Deserialize task operation from JSON string."""
        data = json.loads(task_data)

        # Retain minimal UUID converter for backward compatibility with pre-validation models
        def convert_strings_to_uuids(obj):
            if isinstance(obj, str):
                try:
                    return UUID(obj)
                except ValueError:
                    return obj
            elif isinstance(obj, dict):
                return {k: convert_strings_to_uuids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_strings_to_uuids(item) for item in obj]
            return obj

        operation_type = data.get("operation")
        params = convert_strings_to_uuids(data.get("params", {}))
        trace_id = data.get("trace_id")
        span_id = data.get("span_id")

        if operation_type == "run":
            return _RunTask(
                operation="run", params=params, trace_id=trace_id, span_id=span_id
            )
        elif operation_type == "cancel":
            return _CancelTask(
                operation="cancel", params=params, trace_id=trace_id, span_id=span_id
            )
        elif operation_type == "pause":
            return _PauseTask(
                operation="pause", params=params, trace_id=trace_id, span_id=span_id
            )
        elif operation_type == "resume":
            return _ResumeTask(
                operation="resume", params=params, trace_id=trace_id, span_id=span_id
            )
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")

    async def get_queue_length(self) -> int:
        """Get the current length of the task queue.

        Returns:
            int: Number of tasks in the queue

        Raises:
            RuntimeError: If Redis client is not initialized
        """
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized.")
        return await self._redis_client.llen(self.queue_name)

    async def clear_queue(self) -> int:
        """Clear all tasks from the queue.

        Returns:
            int: Number of tasks removed from the queue

        Raises:
            RuntimeError: If Redis client is not initialized
        """
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized.")
        return await self._redis_client.delete(self.queue_name)

    async def health_check(self) -> bool:
        """Check if the Redis connection is healthy.

        Returns:
            bool: True if Redis is reachable and responsive, False otherwise
        """
        try:
            if not self._redis_client:
                return False
            await self._redis_client.ping()
            return True
        except (redis.RedisError, ConnectionError, TimeoutError, Exception) as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
