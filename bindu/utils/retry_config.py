"""User-configurable retry policies for Bindu agents.

This module extends the existing retry mechanism to support per-agent
configuration via agent_config.json, while maintaining backward compatibility
with the existing app_settings approach.

New Features:
- Per-agent retry configuration
- Custom exception types
- Override default retry policies
- Backward compatible with existing code
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Tuple, Type, TypeVar

from tenacity import (
    AsyncRetrying,
    after_log,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.utils.retry import TRANSIENT_EXCEPTIONS

logger = get_logger("bindu.utils.retry_config")

F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """Configuration for retry behavior loaded from agent config.

    Attributes:
        enabled: Whether retry is enabled (default: True)
        max_attempts: Maximum retry attempts (default: from app_settings)
        min_wait: Minimum wait between retries in seconds
        max_wait: Maximum wait between retries in seconds
        custom_exceptions: Additional exception types to retry

    Example agent_config.json:
        {
            "retry_policy": {
                "enabled": true,
                "max_attempts": 5,
                "min_wait": 1.0,
                "max_wait": 60.0,
                "custom_exceptions": ["requests.RequestException"]
            }
        }
    """

    def __init__(
        self,
        enabled: bool = True,
        max_attempts: int | None = None,
        min_wait: float | None = None,
        max_wait: float | None = None,
        custom_exceptions: Tuple[Type[Exception], ...] = (),
    ):
        """Initialize RetryConfig with given parameters.

        Args:
            enabled: Whether retry is enabled
            max_attempts: Maximum retry attempts
            min_wait: Minimum wait between retries in seconds
            max_wait: Maximum wait between retries in seconds
            custom_exceptions: Additional exception types to retry
        """
        self.enabled = enabled
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.custom_exceptions = custom_exceptions

    @classmethod
    def from_config(cls, config: dict) -> "RetryConfig":
        """Load retry configuration from agent config dictionary.

        Args:
            config: Agent configuration dictionary

        Returns:
            RetryConfig instance

        Example:
            config = {
                "retry_policy": {
                    "enabled": True,
                    "max_attempts": 5,
                }
            }
            retry_config = RetryConfig.from_config(config)
        """
        retry_policy = config.get("retry_policy", {})
        custom_exception_names = retry_policy.get("custom_exceptions", [])
        custom_exceptions = cls._load_exception_classes(custom_exception_names)

        return cls(
            enabled=retry_policy.get("enabled", True),
            max_attempts=retry_policy.get("max_attempts"),
            min_wait=retry_policy.get("min_wait"),
            max_wait=retry_policy.get("max_wait"),
            custom_exceptions=custom_exceptions,
        )

    @staticmethod
    def _load_exception_classes(
        exception_names: list[str],
    ) -> Tuple[Type[Exception], ...]:
        """Load exception classes from their string names.

        Args:
            exception_names: List of exception class names

        Returns:
            Tuple of exception classes
        """
        exceptions = []
        for name in exception_names:
            try:
                if "." in name:
                    module_name, class_name = name.rsplit(".", 1)
                    module = __import__(module_name, fromlist=[class_name])
                    exc_class = getattr(module, class_name)
                else:
                    exc_class = eval(name)  # noqa: S307

                if isinstance(exc_class, type) and issubclass(exc_class, Exception):
                    exceptions.append(exc_class)
                else:
                    logger.warning(f"'{name}' is not an Exception class, skipping")
            except Exception as e:
                logger.warning(f"Could not load exception class '{name}': {e}")

        return tuple(exceptions)

    def get_max_attempts(self, default: int) -> int:
        """Get max attempts, falling back to default if not set."""
        return self.max_attempts if self.max_attempts is not None else default

    def get_min_wait(self, default: float) -> float:
        """Get min wait, falling back to default if not set."""
        return self.min_wait if self.min_wait is not None else default

    def get_max_wait(self, default: float) -> float:
        """Get max wait, falling back to default if not set."""
        return self.max_wait if self.max_wait is not None else default


def retry_with_config(
    retry_config: RetryConfig | None = None,
    operation_type: str = "worker",
) -> Callable[[F], F]:
    """Apply retry logic using the provided agent configuration.

    Extends the existing retry mechanism to support per-agent
    configuration while maintaining backward compatibility.

    Args:
        retry_config: User retry configuration (from agent_config.json)
        operation_type: Type of operation ("worker", "storage", "api", "scheduler")

    Returns:
        Decorated function with retry logic

    Example:
        config = load_agent_config("config.json")
        retry_config = RetryConfig.from_config(config)

        @retry_with_config(retry_config=retry_config, operation_type="api")
        async def call_external_api():
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func, "__name__", str(func))

            if retry_config and not retry_config.enabled:
                logger.debug(f"Retry disabled for {func_name}, executing without retry")
                return await func(*args, **kwargs)

            if operation_type == "worker":
                default_max = app_settings.retry.worker_max_attempts
                default_min = app_settings.retry.worker_min_wait
                default_max_wait = app_settings.retry.worker_max_wait
            elif operation_type == "storage":
                default_max = app_settings.retry.storage_max_attempts
                default_min = app_settings.retry.storage_min_wait
                default_max_wait = app_settings.retry.storage_max_wait
            elif operation_type == "api":
                default_max = app_settings.retry.api_max_attempts
                default_min = app_settings.retry.api_min_wait
                default_max_wait = app_settings.retry.api_max_wait
            elif operation_type == "scheduler":
                default_max = app_settings.retry.scheduler_max_attempts
                default_min = app_settings.retry.scheduler_min_wait
                default_max_wait = app_settings.retry.scheduler_max_wait
            else:
                default_max = 3
                default_min = 1.0
                default_max_wait = 10.0

            if retry_config:
                max_attempts = retry_config.get_max_attempts(default_max)
                min_wait = retry_config.get_min_wait(default_min)
                max_wait = retry_config.get_max_wait(default_max_wait)
            else:
                max_attempts = default_max
                min_wait = default_min
                max_wait = default_max_wait

            if retry_config and retry_config.custom_exceptions:
                retry_exceptions = TRANSIENT_EXCEPTIONS + retry_config.custom_exceptions
                logger.debug(
                    f"Using custom exceptions for {func_name}: "
                    f"{retry_config.custom_exceptions}"
                )
            else:
                retry_exceptions = TRANSIENT_EXCEPTIONS

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_random_exponential(multiplier=1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(retry_exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing {func_name} with config "
                        f"(attempt {attempt.retry_state.attempt_number}/{max_attempts})"
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def load_retry_config_from_agent_config(config: dict) -> RetryConfig:
    """Load and return retry configuration from the agent configuration dictionary.

    Args:
        config: Full agent configuration dictionary

    Returns:
        RetryConfig instance

    Example:
        config = {
            "author": "user@example.com",
            "name": "my_agent",
            "retry_policy": {
                "max_attempts": 5,
                "min_wait": 2.0
            }
        }
        retry_config = load_retry_config_from_agent_config(config)
    """
    return RetryConfig.from_config(config)
