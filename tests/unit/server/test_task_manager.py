"""Minimal tests for TaskManager."""

import uuid
from unittest.mock import AsyncMock, Mock
import pytest

from bindu.server.errors import MalformedContextIdError
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


class TestParseContextId:
    """Validation of `_parse_context_id` — see bugs/known-issues entry
    `context-id-silent-fallback` (resolved by raising MalformedContextIdError
    rather than fabricating a new UUID for malformed input)."""

    def _manager(self):
        return TaskManager(scheduler=Mock(), storage=AsyncMock(), manifest=None)

    def test_none_returns_fresh_uuid(self):
        result = self._manager()._parse_context_id(None)
        assert isinstance(result, uuid.UUID)

    def test_uuid_instance_passes_through(self):
        existing = uuid.uuid4()
        assert self._manager()._parse_context_id(existing) is existing

    def test_valid_uuid_string_parses(self):
        existing = uuid.uuid4()
        result = self._manager()._parse_context_id(str(existing))
        assert result == existing

    def test_malformed_string_raises(self):
        with pytest.raises(MalformedContextIdError) as exc_info:
            self._manager()._parse_context_id("not-a-uuid")
        assert exc_info.value.args[0] == "not-a-uuid"

    def test_non_string_non_uuid_raises(self):
        with pytest.raises(MalformedContextIdError):
            self._manager()._parse_context_id(12345)

    def test_create_error_response_honors_code_override(self):
        response = self._manager()._create_error_response(
            response_class=dict,
            request_id="req-1",
            error_class=dict,
            message="bad",
            code=-32602,
        )
        assert response["error"]["code"] == -32602

    def test_create_error_response_default_code_unchanged(self):
        response = self._manager()._create_error_response(
            response_class=dict,
            request_id="req-1",
            error_class=dict,
            message="bad",
        )
        assert response["error"]["code"] == -32001
