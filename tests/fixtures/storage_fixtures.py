"""Storage-related test fixtures."""

import pytest_asyncio
from typing import AsyncGenerator

from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler


@pytest_asyncio.fixture
async def memory_storage() -> InMemoryStorage:
    """Create an in-memory storage instance for testing.

    Returns:
        InMemoryStorage: Fresh storage instance with no data
    """
    return InMemoryStorage()


@pytest_asyncio.fixture
async def memory_scheduler() -> AsyncGenerator[InMemoryScheduler, None]:
    """Create an in-memory scheduler instance for testing.

    Yields:
        InMemoryScheduler: Scheduler instance within async context
    """
    scheduler = InMemoryScheduler()
    async with scheduler:
        yield scheduler
