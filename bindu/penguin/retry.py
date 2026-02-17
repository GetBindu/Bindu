"""
Retry mechanism for Bindu agent handlers.

Provides automatic retry with exponential backoff when an agent handler
fails due to transient errors (network timeouts, rate limits, etc.).

Usage via config:
    config = {
        ...
        "retry": {
            "enabled": True,
            "max_attempts": 3,
            "backoff_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "max_backoff_seconds": 30.0,
            "retryable_exceptions": []   # empty = retry on ALL exceptions
        }
    }
"""

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for the retry mechanism."""

    def __init__(
        self,
        enabled: bool = True,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: float = 30.0,
        retryable_exceptions: list[type[Exception]] | None = None,
    ) -> None:
        """
        Args:
            enabled: Whether retries are active.
            max_attempts: Total number of attempts (1 = no retries).
            backoff_seconds: Initial wait time between retries in seconds.
            backoff_multiplier: Multiply backoff by this after each failure.
            max_backoff_seconds: Upper limit on wait time between retries.
            retryable_exceptions: Only retry on these exception types.
                                  Empty list / None means retry on ALL exceptions.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds must be >= 0")
        if backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be >= 1")
        if max_backoff_seconds < backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= backoff_seconds")

        self.enabled = enabled
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_seconds = max_backoff_seconds
        self.retryable_exceptions: list[type[Exception]] = retryable_exceptions or []

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "RetryConfig":
        """Build a RetryConfig from a plain dict (as used in agent config.json).

        Args:
            config: Dict with retry settings. Unknown keys are ignored.

        Returns:
            A configured RetryConfig instance.
        """
        return cls(
            enabled=config.get("enabled", True),
            max_attempts=config.get("max_attempts", 3),
            backoff_seconds=float(config.get("backoff_seconds", 1.0)),
            backoff_multiplier=float(config.get("backoff_multiplier", 2.0)),
            max_backoff_seconds=float(config.get("max_backoff_seconds", 30.0)),
            retryable_exceptions=config.get("retryable_exceptions", []),
        )

    def is_retryable(self, exc: Exception) -> bool:
        """Return True if this exception type should trigger a retry."""
        if not self.retryable_exceptions:
            # No filter set — retry on anything
            return True
        return isinstance(exc, tuple(self.retryable_exceptions))


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted.

    Wraps the last exception so callers can inspect the root cause.
    """

    def __init__(self, attempts: int, last_exception: Exception) -> None:
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Handler failed after {attempts} attempt(s). "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )


def with_retry(
    handler: Callable,
    retry_config: RetryConfig,
) -> Callable:
    """Wrap a Bindu handler function with automatic retry logic.

    Returns a new callable with the same signature as the original handler
    but will automatically retry on failure according to retry_config.

    Args:
        handler: The agent handler function to wrap.
        retry_config: Retry settings to apply.

    Returns:
        A wrapped handler that retries on failure.

    Example:
        >>> def my_handler(messages):
        ...     return [{"role": "assistant", "content": "hello"}]
        >>> config = RetryConfig(max_attempts=3, backoff_seconds=1.0)
        >>> safe_handler = with_retry(my_handler, config)
        >>> safe_handler([{"role": "user", "content": "hi"}])
    """
    if not retry_config.enabled:
        # Retry is disabled — return the original handler untouched
        return handler

    def retrying_handler(*args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        wait = retry_config.backoff_seconds

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                result = handler(*args, **kwargs)
                if attempt > 1:
                    logger.info(
                        "Handler succeeded on attempt %d/%d",
                        attempt,
                        retry_config.max_attempts,
                    )
                return result

            except Exception as exc:  # noqa: BLE001
                last_exc = exc

                if not retry_config.is_retryable(exc):
                    logger.warning(
                        "Non-retryable exception on attempt %d/%d: %s: %s",
                        attempt,
                        retry_config.max_attempts,
                        type(exc).__name__,
                        exc,
                    )
                    raise

                if attempt == retry_config.max_attempts:
                    # Final attempt failed — give up
                    break

                logger.warning(
                    "Handler failed on attempt %d/%d — retrying in %.1fs. "
                    "Error: %s: %s",
                    attempt,
                    retry_config.max_attempts,
                    wait,
                    type(exc).__name__,
                    exc,
                )
                time.sleep(wait)
                wait = min(wait * retry_config.backoff_multiplier, retry_config.max_backoff_seconds)

        raise RetryExhaustedError(
            attempts=retry_config.max_attempts,
            last_exception=last_exc,  # type: ignore[arg-type]
        )

    # Preserve the original function's name and docstring
    retrying_handler.__name__ = handler.__name__
    retrying_handler.__doc__ = handler.__doc__
    return retrying_handler


def apply_retry_from_config(
    handler: Callable,
    agent_config: dict[str, Any],
) -> Callable:
    """Read retry settings from an agent config dict and wrap the handler.

    This is the main entry point called inside bindufy() automatically.
    Users never call this directly.

    Args:
        handler: The original agent handler.
        agent_config: The full Bindu agent config dict.

    Returns:
        The handler, wrapped with retry if config["retry"]["enabled"] is True,
        or the original handler if retry config is absent or disabled.

    Example config:
        {
            "retry": {
                "enabled": True,
                "max_attempts": 3,
                "backoff_seconds": 1.0
            }
        }
    """
    retry_dict = agent_config.get("retry", {})

    if not retry_dict or not retry_dict.get("enabled", True):
        logger.debug("Retry is disabled or not configured — skipping.")
        return handler

    retry_config = RetryConfig.from_dict(retry_dict)

    logger.info(
        "Retry enabled: max_attempts=%d, backoff=%.1fs, multiplier=%.1f",
        retry_config.max_attempts,
        retry_config.backoff_seconds,
        retry_config.backoff_multiplier,
    )

    return with_retry(handler, retry_config)
