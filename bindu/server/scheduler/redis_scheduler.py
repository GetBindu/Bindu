"""Redis scheduler implementation for distributed task scheduling."""

from __future__ import annotations as _annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis
from opentelemetry.trace import get_current_span
# # from opentelemetry.propagators.textmap import DefaultTextMapPropagator
# from opentelemetry.propagate import inject, extract
import asyncio

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

class RedisScheduler(Scheduler):
    """A Redis-based scheduler for distributed task operations.

    Uses Redis lists for queue operations with blocking pop for efficient task distribution.
    Suitable for multi-process and multi-worker deployments.
    """

    def __init__(
        self,
        redis_url: str,
        queue_name: str = "bindu:tasks",
        max_connections: int = 10,
        retry_on_timeout: bool = True,
    ):
        """Initialize Redis scheduler.

        Args:
            redis_url: Redis URL (redis://[password@]host:port/db)
            queue_name: Redis queue name for task operations
            max_connections: Maximum Redis connection pool size
            retry_on_timeout: Whether to retry on Redis timeout
        """
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self._redis_client: redis.Redis | None = None

    async def __aenter__(self):
        """Initialize Redis connection pool."""
        self._redis_client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=self.max_connections,
            retry_on_timeout=self.retry_on_timeout,
        )

        # Test connection
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
        """Close Redis connection pool."""
        if self._redis_client:
            await self._redis_client.aclose()
            logger.info("Redis scheduler connection closed")
            self._redis_client = None

    @retry_scheduler_operation(max_attempts=3, min_wait=0.5, max_wait=5)
    async def run_task(self, params: TaskSendParams) -> None:
        """Send a run task operation to Redis queue."""
        logger.debug(f"Scheduling run task: {params}")
        task_operation = _RunTask(
            operation="run", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation(max_attempts=3, min_wait=0.5, max_wait=5)
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Send a cancel task operation to Redis queue."""
        logger.debug(f"Scheduling cancel task: {params}")
        task_operation = _CancelTask(
            operation="cancel", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation(max_attempts=3, min_wait=0.5, max_wait=5)
    async def pause_task(self, params: TaskIdParams) -> None:
        """Send a pause task operation to Redis queue."""
        logger.debug(f"Scheduling pause task: {params}")
        task_operation = _PauseTask(
            operation="pause", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    @retry_scheduler_operation(max_attempts=3, min_wait=0.5, max_wait=5)
    async def resume_task(self, params: TaskIdParams) -> None:
        """Send a resume task operation to Redis queue."""
        logger.debug(f"Scheduling resume task: {params}")
        task_operation = _ResumeTask(
            operation="resume", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from Redis queue using blocking pop."""
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        logger.info(
            f"Starting to receive task operations from queue: {self.queue_name}"
        )

        backoff = 1.0 

        while True:
            try:
                # Blocking pop with 1 second timeout
                result = await self._redis_client.blpop(self.queue_name, timeout=1)

                if result:
                    _, task_data = result
                    task_operation = self._deserialize_task_operation(task_data)
                    logger.debug(
                        f"Received task operation: {task_operation['operation']}"
                    )
                    backoff = 1.0 
                    yield task_operation

            except redis.RedisError as e:
                logger.error(f"Redis error in receive_task_operations: {e}")
                backoff = min(backoff * 2, 30.0)
                logger.warning(f"Backing off for {backoff:.1f}s before retrying...")
                await asyncio.sleep(backoff)
                continue
            except json.JSONDecodeError as e:
                # Log deserialization errors but continue
                logger.error(f"Failed to deserialize task operation: {e}")
                continue
            except Exception as e:
                # Log unexpected errors
                logger.error(f"Unexpected error in receive_task_operations: {e}")
                continue

    async def _push_task_operation(self, task_operation: TaskOperation) -> None:
        """Push a task operation to Redis queue."""
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
        except Exception as e:
            logger.error(f"Failed to serialize task operation: {e}")
            raise

    def _serialize_task_operation(self, task_operation: TaskOperation) -> str:
        """Serialize task operation to JSON string for Redis storage."""
        from uuid import UUID

        # Inject W3C trace context into carrier
        carrier: dict[str, str] = {}
        try:
            from opentelemetry.propagate import inject
            inject(carrier)
        except (ModuleNotFoundError, Exception):
            pass  # Degrade gracefully if opentelemetry not available

        def convert_uuids(obj):
            """Recursively convert UUIDs to strings in nested structures."""
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_uuids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_uuids(item) for item in obj]
            return obj

        serializable_task = {
            "operation": task_operation["operation"],
            "params": convert_uuids(task_operation["params"]),
            "trace_context": carrier,
        }
        return json.dumps(serializable_task)

    def _deserialize_task_operation(self, task_data: str) -> TaskOperation:
        """Deserialize task operation from JSON string."""
        from uuid import UUID

        data = json.loads(task_data)

        def convert_strings_to_uuids(obj):
            """Recursively convert UUID strings back to UUID objects."""
            if isinstance(obj, str):
                try:
                    return UUID(obj)
                except (ValueError, AttributeError):
                    return obj
            elif isinstance(obj, dict):
                return {k: convert_strings_to_uuids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_strings_to_uuids(item) for item in obj]
            return obj

        # Extract and restore W3C trace context
        trace_context = data.get("trace_context", {})
        try:
            from opentelemetry.propagate import extract
            from opentelemetry import context
            ctx = extract(trace_context)
            token = context.attach(ctx)
            try:
                current_span = get_current_span()
            finally:
                context.detach(token)
        except (ModuleNotFoundError, Exception):
            current_span = get_current_span()

        operation_type = data["operation"]
        params = convert_strings_to_uuids(data["params"])

        if operation_type == "run":
            return _RunTask(
                operation="run", params=params, _current_span=current_span
            )
        elif operation_type == "cancel":
            return _CancelTask(
                operation="cancel", params=params, _current_span=current_span
            )
        elif operation_type == "pause":
            return _PauseTask(
                operation="pause", params=params, _current_span=current_span
            )
        elif operation_type == "resume":
            return _ResumeTask(
                operation="resume", params=params, _current_span=current_span
            )
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")

    async def get_queue_length(self) -> int:
        """Get the current length of the task queue."""
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        return await self._redis_client.llen(self.queue_name)

    async def clear_queue(self) -> int:
        """Clear all tasks from the queue. Returns number of tasks removed."""
        if not self._redis_client:
            raise RuntimeError(
                "Redis client not initialized. Use async context manager."
            )

        return await self._redis_client.delete(self.queue_name)

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if not self._redis_client:
                return False
            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
