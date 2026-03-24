"""Minimal tests for TaskManager."""

from unittest.mock import AsyncMock, Mock
import pytest

from bindu.server.task_manager import TaskManager


class TestTaskManager:
    """Test TaskManager functionality."""

    def test_task_manager_initialization(self):
        """Test TaskManager initializes correctly."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert manager.scheduler == mock_scheduler
        assert manager.storage == mock_storage
        assert manager.manifest is None

    def test_task_manager_with_manifest(self):
        """Test TaskManager initializes with manifest."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_manifest = Mock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=mock_manifest
        )

        assert manager.manifest == mock_manifest

    @pytest.mark.asyncio
    async def test_task_manager_context_manager(self):
        """Test TaskManager async context manager."""
        mock_scheduler = AsyncMock()
        mock_scheduler.__aenter__ = AsyncMock(return_value=mock_scheduler)
        mock_scheduler.__aexit__ = AsyncMock(return_value=None)
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        async with manager as m:
            assert m == manager

        mock_scheduler.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_manager_initialization(self):
        """Test push manager is initialized."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert manager._push_manager is not None
        assert manager._push_manager.storage == mock_storage

    @pytest.mark.asyncio
    async def test_context_manager_calls_scheduler_exit(self):
        """Test that context manager exit calls scheduler exit."""
        mock_scheduler = AsyncMock()
        mock_scheduler.__aenter__ = AsyncMock(return_value=mock_scheduler)
        mock_scheduler.__aexit__ = AsyncMock(return_value=None)
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        async with manager:
            pass

        mock_scheduler.__aexit__.assert_called_once()

    def test_task_manager_has_push_manager(self):
        """Test that task manager has push manager attribute."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert hasattr(manager, "_push_manager")

    def test_task_manager_storage_attribute(self):
        """Test that storage is accessible."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert manager.storage == mock_storage

    def test_task_manager_scheduler_attribute(self):
        """Test that scheduler is accessible."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert manager.scheduler == mock_scheduler

    def test_task_manager_with_none_manifest(self):
        """Test task manager works with None manifest."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=None
        )

        assert manager.manifest is None

    def test_task_manager_initialization_sets_attributes(self):
        """Test that initialization sets all required attributes."""
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_manifest = Mock()

        manager = TaskManager(
            scheduler=mock_scheduler, storage=mock_storage, manifest=mock_manifest
        )

        assert hasattr(manager, "scheduler")
        assert hasattr(manager, "storage")
        assert hasattr(manager, "manifest")
        assert hasattr(manager, "_push_manager")
