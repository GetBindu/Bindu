"""Tests for retry utilities."""

import pytest

from bindu.utils.retry import create_retry_decorator


class TestRetryDecorators:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_create_retry_decorator_storage(self):
        """Test creating storage retry decorator."""
        decorator = create_retry_decorator(
            "storage", max_attempts=3, min_wait=0.1, max_wait=1.0
        )

        @decorator
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_create_retry_decorator_worker(self):
        """Test creating worker retry decorator."""
        decorator = create_retry_decorator(
            "worker", max_attempts=3, min_wait=0.1, max_wait=1.0
        )

        @decorator
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_create_retry_decorator_api(self):
        """Test creating API retry decorator."""
        decorator = create_retry_decorator(
            "api", max_attempts=3, min_wait=0.1, max_wait=1.0
        )

        @decorator
        async def test_func(value):
            return value * 2

        result = await test_func(21)
        assert result == 42
