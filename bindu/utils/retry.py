"""Retry configuration and decorators using Tenacity.

This module provides retry mechanisms for various operations in Bindu:
- Worker task execution
- Storage operations (database, redis)
- External API calls
- Scheduler operations

Retry Strategies:
- Exponential backoff with jitter
- Configurable max attempts
- Custom retry conditions
- Logging and observability integration
"""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)
from tenacity.wait import wait_random_exponential

from bindu.utils.exceptions import (
    HTTPConnectionError,
    HTTPTimeoutError,
    HTTPServerError,
)
from bindu.utils.logging import get_logger
from bindu.settings import app_settings

logger = get_logger("bindu.utils.retry")

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])

# Common transient errors that should trigger retries
# Note: Only includes truly transient errors (network, timeout, connection)
# Application logic errors (ValueError, KeyError, etc.) should not be retried
TRANSIENT_EXCEPTIONS = (
    # Network errors
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    ConnectionAbortedError,
    # Timeout errors
    TimeoutError,
    asyncio.TimeoutError,
    # OS errors
    OSError,  # Covers BrokenPipeError, etc.
)

# HTTP-specific retryable exceptions
HTTP_RETRYABLE_EXCEPTIONS = TRANSIENT_EXCEPTIONS + (
    HTTPConnectionError,
    HTTPTimeoutError,
    HTTPServerError,  # 5xx errors are retryable
)


def create_retry_decorator(
    operation_type: str,
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
    use_jitter: bool = True,
) -> Callable[[F], F]:
    """Create retry decorators with consistent behavior.

    This replaces the duplicate retry_worker_operation, retry_storage_operation,
    retry_scheduler_operation, and retry_api_call decorators.

    Args:
        operation_type: Type of operation ('worker', 'storage', 'scheduler', 'api')
        max_attempts: Maximum number of retry attempts (uses settings default if None)
        min_wait: Minimum wait time between retries in seconds (uses settings default if None)
        max_wait: Maximum wait time between retries in seconds (uses settings default if None)
        use_jitter: Whether to use random exponential backoff (True) or regular exponential (False)

    Returns:
        Decorated function with retry logic

    Example:
        @create_retry_decorator('worker')
        async def run_task(self, params):
            # Task execution logic
            pass
    """
    # Map operation types to settings
    settings_map = {
        "worker": ("worker_max_attempts", "worker_min_wait", "worker_max_wait"),
        "storage": ("storage_max_attempts", "storage_min_wait", "storage_max_wait"),
        "scheduler": (
            "scheduler_max_attempts",
            "scheduler_min_wait",
            "scheduler_max_wait",
        ),
        "api": ("api_max_attempts", "api_min_wait", "api_max_wait"),
    }

    if operation_type not in settings_map:
        raise ValueError(
            f"Invalid operation_type: {operation_type}. "
            f"Must be one of: {', '.join(settings_map.keys())}"
        )

    max_key, min_key, max_wait_key = settings_map[operation_type]

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get retry parameters from settings or use provided values
            _max_attempts = max_attempts or getattr(app_settings.retry, max_key)
            _min_wait = min_wait or getattr(app_settings.retry, min_key)
            _max_wait = max_wait or getattr(app_settings.retry, max_wait_key)

            # Choose wait strategy based on use_jitter
            wait_strategy = (
                wait_random_exponential(multiplier=1, min=_min_wait, max=_max_wait)
                if use_jitter
                else wait_exponential(multiplier=1, min=_min_wait, max=_max_wait)
            )

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_strategy,
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing {operation_type} operation {func.__name__} "
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience decorators using the factory (backward compatibility)
def retry_worker_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for worker task execution operations.

    Retries on transient failures with exponential backoff and jitter.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic
    """
    return create_retry_decorator(
        "worker", max_attempts, min_wait, max_wait, use_jitter=True
    )


def retry_storage_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for storage operations (database, redis).

    Handles transient database connection issues, deadlocks, and timeouts.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic
    """
    return create_retry_decorator(
        "storage", max_attempts, min_wait, max_wait, use_jitter=False
    )


def retry_scheduler_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for scheduler operations.

    Handles transient failures in task scheduling and broker communication.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic
    """
    return create_retry_decorator(
        "scheduler", max_attempts, min_wait, max_wait, use_jitter=True
    )


def retry_api_call(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for external API calls.

    Handles transient network failures, rate limits, and timeouts.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic
    """
    return create_retry_decorator(
        "api", max_attempts, min_wait, max_wait, use_jitter=True
    )


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic.

    Utility function for ad-hoc retry logic without decorators.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function execution

    Raises:
        RetryError: If all retry attempts fail

    Example:
        result = await execute_with_retry(
            some_async_function,
            arg1, arg2,
            max_attempts=5,
            kwarg1=value1
        )
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    ):
        with attempt:
            logger.debug(
                f"Executing {func.__name__} "  # type: ignore[attr-defined]
                f"(attempt {attempt.retry_state.attempt_number}/{max_attempts})"
            )
            return await func(*args, **kwargs)
