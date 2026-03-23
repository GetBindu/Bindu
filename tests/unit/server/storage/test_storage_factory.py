"""Minimal tests for storage factory."""

import pytest
from unittest.mock import AsyncMock, patch

from bindu.server.storage.factory import create_storage, close_storage
from bindu.server.storage.memory_storage import InMemoryStorage


class TestStorageFactory:
    """Test storage factory functionality."""

    @pytest.mark.asyncio
    async def test_create_memory_storage(self):
        """Test creating memory storage from settings."""
        with patch("bindu.server.storage.factory.app_settings") as mock_settings:
            mock_settings.storage.backend = "memory"

            storage = await create_storage()

            assert isinstance(storage, InMemoryStorage)

    @pytest.mark.asyncio
    async def test_create_storage_invalid_backend_raises(self):
        """Test that invalid backend raises ValueError."""
        with patch("bindu.server.storage.factory.app_settings") as mock_settings:
            mock_settings.storage.backend = "invalid"

            with pytest.raises(ValueError, match="Unknown storage backend"):
                await create_storage()

    @pytest.mark.asyncio
    async def test_create_postgres_storage_without_sqlalchemy_raises(self):
        """Test that Postgres storage without SQLAlchemy raises error."""
        with patch("bindu.server.storage.factory.app_settings") as mock_settings:
            mock_settings.storage.backend = "postgres"

            with patch("bindu.server.storage.factory.POSTGRES_AVAILABLE", False):
                with pytest.raises(ValueError, match="requires SQLAlchemy"):
                    await create_storage()

    @pytest.mark.asyncio
    async def test_create_postgres_storage_without_url_raises(self):
        """Test that Postgres storage without URL raises error."""
        with patch("bindu.server.storage.factory.app_settings") as mock_settings:
            mock_settings.storage.backend = "postgres"
            mock_settings.storage.postgres_url = None

            with patch("bindu.server.storage.factory.POSTGRES_AVAILABLE", True):
                with pytest.raises(ValueError, match="requires a database URL"):
                    await create_storage()

    @pytest.mark.asyncio
    async def test_close_storage(self):
        """Test closing storage gracefully."""
        mock_storage = AsyncMock()
        mock_storage.close = AsyncMock()

        await close_storage(mock_storage)

        mock_storage.close.assert_called_once()
