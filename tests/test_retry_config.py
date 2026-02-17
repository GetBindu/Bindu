"""Tests for retry_config module."""

import pytest
from bindu.utils.retry_config import (
    RetryConfig,
    load_retry_config_from_agent_config,
    retry_with_config,
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.enabled is True
        assert config.max_attempts is None
        assert config.min_wait is None
        assert config.max_wait is None
        assert config.custom_exceptions == ()

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            enabled=False,
            max_attempts=10,
            min_wait=2.0,
            max_wait=120.0,
            custom_exceptions=(ValueError, KeyError),
        )
        assert config.enabled is False
        assert config.max_attempts == 10
        assert config.min_wait == 2.0
        assert config.max_wait == 120.0
        assert config.custom_exceptions == (ValueError, KeyError)

    def test_from_config_empty(self):
        """Test loading from empty config."""
        config_dict: dict = {}
        retry_config = RetryConfig.from_config(config_dict)
        assert retry_config.enabled is True
        assert retry_config.max_attempts is None
        assert retry_config.min_wait is None
        assert retry_config.max_wait is None

    def test_from_config_with_values(self):
        """Test loading from config with values."""
        config_dict = {
            "retry_policy": {
                "enabled": False,
                "max_attempts": 7,
                "min_wait": 3.0,
                "max_wait": 90.0,
            }
        }
        retry_config = RetryConfig.from_config(config_dict)
        assert retry_config.enabled is False
        assert retry_config.max_attempts == 7
        assert retry_config.min_wait == 3.0
        assert retry_config.max_wait == 90.0

    def test_from_config_with_custom_exceptions(self):
        """Test loading with custom exception names."""
        config_dict = {
            "retry_policy": {"custom_exceptions": ["ValueError", "TypeError"]}
        }
        retry_config = RetryConfig.from_config(config_dict)
        assert ValueError in retry_config.custom_exceptions
        assert TypeError in retry_config.custom_exceptions

    def test_get_methods_with_none(self):
        """Test get methods with None values."""
        config = RetryConfig()
        assert config.get_max_attempts(5) == 5
        assert config.get_min_wait(1.0) == 1.0
        assert config.get_max_wait(10.0) == 10.0

    def test_get_methods_with_values(self):
        """Test get methods with set values."""
        config = RetryConfig(
            max_attempts=10,
            min_wait=2.0,
            max_wait=20.0,
        )
        assert config.get_max_attempts(5) == 10
        assert config.get_min_wait(1.0) == 2.0
        assert config.get_max_wait(10.0) == 20.0


class TestLoadRetryConfigFromAgentConfig:
    """Test loading retry config from agent configuration."""

    def test_load_empty_config(self):
        """Test loading from empty config."""
        config: dict = {}
        retry_config = load_retry_config_from_agent_config(config)
        assert retry_config.enabled is True
        assert retry_config.max_attempts is None

    def test_load_full_config(self):
        """Test loading complete configuration."""
        config = {
            "author": "test@example.com",
            "name": "test_agent",
            "retry_policy": {
                "enabled": True,
                "max_attempts": 5,
                "min_wait": 1.5,
                "max_wait": 30.0,
            },
        }
        retry_config = load_retry_config_from_agent_config(config)
        assert retry_config.enabled is True
        assert retry_config.max_attempts == 5
        assert retry_config.min_wait == 1.5
        assert retry_config.max_wait == 30.0


@pytest.mark.asyncio
async def test_retry_with_config_disabled() -> None:
    """Test that retry is skipped when disabled."""
    config = RetryConfig(enabled=False)
    counter = [0]

    @retry_with_config(retry_config=config, operation_type="worker")
    async def test_func() -> str:
        counter[0] += 1
        if counter[0] == 1:
            raise ConnectionError("Should not retry")
        return "success"

    with pytest.raises(ConnectionError):
        await test_func()

    assert counter[0] == 1


@pytest.mark.asyncio
async def test_retry_with_config_enabled() -> None:
    """Test that retry works when enabled."""
    config = RetryConfig(enabled=True, max_attempts=3, min_wait=0.01, max_wait=0.1)
    counter = [0]

    @retry_with_config(retry_config=config, operation_type="worker")
    async def test_func() -> str:
        counter[0] += 1
        if counter[0] < 3:
            raise ConnectionError("Retry me")
        return "success"

    result = await test_func()
    assert result == "success"
    assert counter[0] == 3
