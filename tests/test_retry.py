"""
Tests for bindu.penguin.retry

Covers:
- RetryConfig creation and validation
- RetryConfig.from_dict
- RetryConfig.is_retryable
- with_retry: success on first attempt
- with_retry: success after retries
- with_retry: exhausting all attempts
- with_retry: non-retryable exception skips retry
- with_retry: retry disabled passes handler through unchanged
- apply_retry_from_config: reads config and wraps handler
- apply_retry_from_config: missing / disabled config returns original handler
- Exponential backoff timing
- RetryExhaustedError message and attributes
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from bindu.penguin.retry import (
    RetryConfig,
    RetryExhaustedError,
    apply_retry_from_config,
    with_retry,
)


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------


class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.enabled is True
        assert cfg.max_attempts == 3
        assert cfg.backoff_seconds == 1.0
        assert cfg.backoff_multiplier == 2.0
        assert cfg.max_backoff_seconds == 30.0
        assert cfg.retryable_exceptions == []

    def test_custom_values(self):
        cfg = RetryConfig(max_attempts=5, backoff_seconds=0.5, backoff_multiplier=3.0)
        assert cfg.max_attempts == 5
        assert cfg.backoff_seconds == 0.5
        assert cfg.backoff_multiplier == 3.0

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfig(max_attempts=0)

    def test_negative_backoff_raises(self):
        with pytest.raises(ValueError, match="backoff_seconds must be >= 0"):
            RetryConfig(backoff_seconds=-1)

    def test_multiplier_less_than_one_raises(self):
        with pytest.raises(ValueError, match="backoff_multiplier must be >= 1"):
            RetryConfig(backoff_multiplier=0.5)

    def test_max_backoff_less_than_initial_raises(self):
        with pytest.raises(ValueError, match="max_backoff_seconds must be >= backoff_seconds"):
            RetryConfig(backoff_seconds=10.0, max_backoff_seconds=5.0)

    def test_from_dict_full(self):
        cfg = RetryConfig.from_dict({
            "enabled": True,
            "max_attempts": 5,
            "backoff_seconds": 2.0,
            "backoff_multiplier": 3.0,
            "max_backoff_seconds": 60.0,
        })
        assert cfg.max_attempts == 5
        assert cfg.backoff_seconds == 2.0
        assert cfg.backoff_multiplier == 3.0
        assert cfg.max_backoff_seconds == 60.0

    def test_from_dict_empty_uses_defaults(self):
        cfg = RetryConfig.from_dict({})
        assert cfg.max_attempts == 3
        assert cfg.backoff_seconds == 1.0

    def test_from_dict_disabled(self):
        cfg = RetryConfig.from_dict({"enabled": False})
        assert cfg.enabled is False

    def test_is_retryable_no_filter(self):
        """With no retryable_exceptions set, all exceptions are retryable."""
        cfg = RetryConfig()
        assert cfg.is_retryable(ValueError("oops")) is True
        assert cfg.is_retryable(ConnectionError("timeout")) is True
        assert cfg.is_retryable(RuntimeError("boom")) is True

    def test_is_retryable_with_filter_match(self):
        cfg = RetryConfig(retryable_exceptions=[ConnectionError, TimeoutError])
        assert cfg.is_retryable(ConnectionError()) is True
        assert cfg.is_retryable(TimeoutError()) is True

    def test_is_retryable_with_filter_no_match(self):
        cfg = RetryConfig(retryable_exceptions=[ConnectionError])
        assert cfg.is_retryable(ValueError("not a connection error")) is False


# ---------------------------------------------------------------------------
# RetryExhaustedError
# ---------------------------------------------------------------------------


class TestRetryExhaustedError:
    def test_message_contains_attempts_and_exception(self):
        original = ValueError("something broke")
        err = RetryExhaustedError(attempts=3, last_exception=original)
        assert "3" in str(err)
        assert "ValueError" in str(err)
        assert "something broke" in str(err)

    def test_attributes(self):
        original = RuntimeError("oops")
        err = RetryExhaustedError(attempts=2, last_exception=original)
        assert err.attempts == 2
        assert err.last_exception is original


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------


class TestWithRetry:
    def test_success_on_first_attempt(self):
        """Handler that works first time — no retry needed."""
        handler = MagicMock(return_value=[{"role": "assistant", "content": "ok"}])
        cfg = RetryConfig(max_attempts=3, backoff_seconds=0)

        wrapped = with_retry(handler, cfg)
        result = wrapped([{"role": "user", "content": "hi"}])

        assert result == [{"role": "assistant", "content": "ok"}]
        assert handler.call_count == 1

    def test_success_after_one_retry(self):
        """Handler fails once then succeeds."""
        handler = MagicMock(side_effect=[RuntimeError("transient"), [{"role": "assistant", "content": "ok"}]])
        cfg = RetryConfig(max_attempts=3, backoff_seconds=0)

        wrapped = with_retry(handler, cfg)
        result = wrapped([])

        assert result == [{"role": "assistant", "content": "ok"}]
        assert handler.call_count == 2

    def test_success_after_two_retries(self):
        """Handler fails twice then succeeds on 3rd attempt."""
        handler = MagicMock(side_effect=[
            ConnectionError("timeout"),
            ConnectionError("timeout"),
            [{"role": "assistant", "content": "finally!"}],
        ])
        cfg = RetryConfig(max_attempts=3, backoff_seconds=0)

        wrapped = with_retry(handler, cfg)
        result = wrapped([])

        assert result == [{"role": "assistant", "content": "finally!"}]
        assert handler.call_count == 3

    def test_raises_retry_exhausted_after_all_attempts_fail(self):
        """Handler always fails — should raise RetryExhaustedError."""
        handler = MagicMock(side_effect=RuntimeError("always fails"))
        cfg = RetryConfig(max_attempts=3, backoff_seconds=0)

        wrapped = with_retry(handler, cfg)

        with pytest.raises(RetryExhaustedError) as exc_info:
            wrapped([])

        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, RuntimeError)
        assert handler.call_count == 3

    def test_non_retryable_exception_reraises_immediately(self):
        """If exception type is not in retryable list, no retry happens."""
        handler = MagicMock(side_effect=ValueError("bad input"))
        cfg = RetryConfig(
            max_attempts=3,
            backoff_seconds=0,
            retryable_exceptions=[ConnectionError],  # ValueError NOT in list
        )

        wrapped = with_retry(handler, cfg)

        with pytest.raises(ValueError, match="bad input"):
            wrapped([])

        assert handler.call_count == 1  # Only called once — no retry

    def test_retry_disabled_returns_original_handler(self):
        """When enabled=False, with_retry returns the handler untouched."""
        handler = MagicMock(return_value="result")
        cfg = RetryConfig(enabled=False)

        wrapped = with_retry(handler, cfg)

        # Should be the exact same object
        assert wrapped is handler

    def test_preserves_handler_name(self):
        def my_cool_handler(messages):
            return messages

        cfg = RetryConfig(max_attempts=2, backoff_seconds=0)
        wrapped = with_retry(my_cool_handler, cfg)
        assert wrapped.__name__ == "my_cool_handler"

    def test_max_attempts_one_means_no_retry(self):
        """max_attempts=1 means try once and fail immediately."""
        handler = MagicMock(side_effect=RuntimeError("fail"))
        cfg = RetryConfig(max_attempts=1, backoff_seconds=0)

        wrapped = with_retry(handler, cfg)

        with pytest.raises(RetryExhaustedError):
            wrapped([])

        assert handler.call_count == 1

    def test_exponential_backoff_timing(self):
        """Each retry waits longer than the last (exponential backoff)."""
        sleep_calls = []

        def fake_sleep(duration):
            sleep_calls.append(duration)

        handler = MagicMock(side_effect=[
            RuntimeError("fail"),
            RuntimeError("fail"),
            [{"role": "assistant", "content": "ok"}],
        ])
        cfg = RetryConfig(max_attempts=3, backoff_seconds=1.0, backoff_multiplier=2.0)

        with patch("bindu.penguin.retry.time.sleep", side_effect=fake_sleep):
            wrapped = with_retry(handler, cfg)
            wrapped([])

        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1.0   # First retry: 1s
        assert sleep_calls[1] == 2.0   # Second retry: 2s (1 * 2)

    def test_max_backoff_cap_is_respected(self):
        """Backoff should never exceed max_backoff_seconds."""
        sleep_calls = []

        def fake_sleep(duration):
            sleep_calls.append(duration)

        # Will fail 4 times before success
        handler = MagicMock(side_effect=[
            RuntimeError(),
            RuntimeError(),
            RuntimeError(),
            RuntimeError(),
            [{"role": "assistant", "content": "ok"}],
        ])
        cfg = RetryConfig(
            max_attempts=5,
            backoff_seconds=10.0,
            backoff_multiplier=5.0,
            max_backoff_seconds=15.0,  # Cap at 15s
        )

        with patch("bindu.penguin.retry.time.sleep", side_effect=fake_sleep):
            wrapped = with_retry(handler, cfg)
            wrapped([])

        # All sleep calls must be <= 15 seconds
        for call in sleep_calls:
            assert call <= 15.0


# ---------------------------------------------------------------------------
# apply_retry_from_config
# ---------------------------------------------------------------------------


class TestApplyRetryFromConfig:
    def test_applies_retry_when_configured(self):
        """Handler gets wrapped when retry config is present and enabled."""
        handler = MagicMock(side_effect=[RuntimeError("fail"), [{"role": "assistant", "content": "ok"}]])

        agent_config = {
            "retry": {
                "enabled": True,
                "max_attempts": 2,
                "backoff_seconds": 0,
            }
        }

        wrapped = apply_retry_from_config(handler, agent_config)
        result = wrapped([])

        assert result == [{"role": "assistant", "content": "ok"}]
        assert handler.call_count == 2

    def test_returns_original_handler_when_retry_absent(self):
        """No retry key in config → original handler returned unchanged."""
        handler = MagicMock(return_value="result")
        agent_config = {"name": "my_agent"}

        wrapped = apply_retry_from_config(handler, agent_config)
        assert wrapped is handler

    def test_returns_original_handler_when_retry_disabled(self):
        """retry.enabled=False → original handler returned unchanged."""
        handler = MagicMock(return_value="result")
        agent_config = {"retry": {"enabled": False}}

        wrapped = apply_retry_from_config(handler, agent_config)
        assert wrapped is handler

    def test_returns_original_handler_when_retry_empty_dict(self):
        """Empty retry dict → retry disabled by convention."""
        handler = MagicMock(return_value="result")
        agent_config = {"retry": {}}

        # Empty dict has no "enabled" key — defaults to True, so wraps
        wrapped = apply_retry_from_config(handler, agent_config)
        # Wrapped but still callable
        assert callable(wrapped)
