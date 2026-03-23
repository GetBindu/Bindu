"""Minimal tests for scheduler factory."""

import pytest
from unittest.mock import Mock, patch

from bindu.server.scheduler.factory import create_scheduler, close_scheduler
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.common.models import SchedulerConfig


class TestSchedulerFactory:
    """Test scheduler factory functionality."""

    @pytest.mark.asyncio
    async def test_create_memory_scheduler_from_config(self):
        """Test creating memory scheduler from config."""
        config = SchedulerConfig(type="memory")

        scheduler = await create_scheduler(config)

        assert isinstance(scheduler, InMemoryScheduler)

    @pytest.mark.asyncio
    async def test_create_scheduler_invalid_backend_raises(self):
        """Test that invalid backend raises ValueError."""
        config = SchedulerConfig(type="invalid")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="Unknown scheduler backend"):
            await create_scheduler(config)

    @pytest.mark.asyncio
    async def test_create_redis_scheduler_without_redis_raises(self):
        """Test that Redis scheduler without redis package raises error."""
        config = SchedulerConfig(type="redis", redis_url="redis://localhost:6379/0")

        with patch("bindu.server.scheduler.factory.REDIS_AVAILABLE", False):
            with pytest.raises(ValueError, match="requires redis package"):
                await create_scheduler(config)

    @pytest.mark.asyncio
    async def test_create_redis_scheduler_constructs_url_from_components(self):
        """Test that Redis scheduler can construct URL from components."""
        config = SchedulerConfig(
            type="redis", redis_host="localhost", redis_port=6379, redis_db=0
        )

        with patch("bindu.server.scheduler.factory.REDIS_AVAILABLE", True):
            with patch("bindu.server.scheduler.factory.RedisScheduler") as mock_redis:
                await create_scheduler(config)

                # Verify RedisScheduler was called with constructed URL
                mock_redis.assert_called_once()
                call_kwargs = mock_redis.call_args[1]
                assert "redis_url" in call_kwargs
                assert call_kwargs["redis_url"] == "redis://localhost:6379/0"

    @pytest.mark.asyncio
    async def test_close_scheduler(self):
        """Test closing scheduler gracefully."""
        mock_scheduler = Mock()
        mock_scheduler.__aexit__ = Mock(return_value=None)

        await close_scheduler(mock_scheduler)

        mock_scheduler.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_close_scheduler_handles_errors(self):
        """Test that close_scheduler handles errors gracefully."""
        mock_scheduler = Mock()
        mock_scheduler.__aexit__ = Mock(side_effect=Exception("Close error"))

        # Should not raise, just log error
        await close_scheduler(mock_scheduler)

        mock_scheduler.__aexit__.assert_called_once()
