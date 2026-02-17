"""Synchronous retry decorators for non-async operations.

This module provides synchronous versions of the retry decorators,
complementing the existing async-only retry mechanism.

Use Cases:
- Synchronous API clients
- File I/O operations
- Synchronous database queries
- Legacy code integration
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from tenacity import (
    Retrying,
    after_log,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.utils.retry import TRANSIENT_EXCEPTIONS

logger = get_logger("bindu.utils.retry_sync")

F = TypeVar("F", bound=Callable[..., Any])


def retry_sync_worker_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry a worker operation with exponential backoff.

    Use this for synchronous functions that need retry logic.
    For async functions, use retry_worker_operation from bindu.utils.retry.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_sync_worker_operation()
        def process_file(filepath):
            with open(filepath) as f:
                return f.read()
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.worker_max_attempts
            _min_wait = min_wait or app_settings.retry.worker_min_wait
            _max_wait = max_wait or app_settings.retry.worker_max_wait
            func_name = getattr(func, "__name__", str(func))
            for attempt in Retrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing {func_name} "
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def retry_sync_storage_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry a storage operation with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_sync_storage_operation()
        def update_database(record_id, data):
            # Synchronous database update
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.storage_max_attempts
            _min_wait = min_wait or app_settings.retry.storage_min_wait
            _max_wait = max_wait or app_settings.retry.storage_max_wait
            func_name = getattr(func, "__name__", str(func))
            for attempt in Retrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing storage operation {func_name} "
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def retry_sync_api_call(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry an external API call with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_sync_api_call()
        def call_rest_api(endpoint, data):
            import requests
            return requests.post(endpoint, json=data)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.api_max_attempts
            _min_wait = min_wait or app_settings.retry.api_min_wait
            _max_wait = max_wait or app_settings.retry.api_max_wait
            func_name = getattr(func, "__name__", str(func))
            for attempt in Retrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing API call {func_name} "
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def execute_sync_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    **kwargs: Any,
) -> Any:
    """Execute a synchronous function with retry logic.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function execution

    Example:
        result = execute_sync_with_retry(
            some_function,
            arg1, arg2,
            max_attempts=5,
            kwarg1=value1
        )
    """
    func_name = getattr(func, "__name__", str(func))
    for attempt in Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    ):
        with attempt:
            logger.debug(
                f"Executing {func_name} "
                f"(attempt {attempt.retry_state.attempt_number}/{max_attempts})"
            )
            return func(*args, **kwargs)
