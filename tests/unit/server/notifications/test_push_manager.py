"""Minimal tests for push notification manager."""

from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest

from bindu.common.protocol.types import PushNotificationConfig
from bindu.server.notifications.push_manager import PushNotificationManager


class TestPushNotificationManager:
    """Test push notification manager functionality."""

    def test_manager_initialization(self):
        """Test manager initializes with default values."""
        manager = PushNotificationManager()

        assert manager.manifest is None
        assert manager.storage is None
        assert manager.notification_service is not None
        assert len(manager._push_notification_configs) == 0
        assert len(manager._notification_sequences) == 0

    def test_manager_initialization_with_manifest(self):
        """Test manager initialization with manifest."""
        mock_manifest = Mock()
        manager = PushNotificationManager(manifest=mock_manifest)

        assert manager.manifest == mock_manifest

    @pytest.mark.asyncio
    async def test_initialize_without_storage(self):
        """Test initialize skips loading when no storage configured."""
        manager = PushNotificationManager()

        await manager.initialize()

        # Should complete without error
        assert len(manager._push_notification_configs) == 0

    @pytest.mark.asyncio
    async def test_initialize_with_storage(self):
        """Test initialize loads configs from storage."""
        mock_storage = AsyncMock()
        mock_storage.load_all_webhook_configs.return_value = {}

        manager = PushNotificationManager(storage=mock_storage)

        await manager.initialize()

        mock_storage.load_all_webhook_configs.assert_called_once()

    def test_is_push_supported_without_manifest(self):
        """Test push support check without manifest."""
        manager = PushNotificationManager()

        assert manager.is_push_supported() is False

    def test_is_push_supported_with_manifest(self):
        """Test push support check with manifest."""
        mock_manifest = Mock()
        mock_manifest.capabilities = {"push_notifications": True}

        manager = PushNotificationManager(manifest=mock_manifest)

        assert manager.is_push_supported() is True

    def test_get_global_webhook_config_without_manifest(self):
        """Test getting global webhook config without manifest."""
        manager = PushNotificationManager()

        config = manager.get_global_webhook_config()

        assert config is None

    def test_get_global_webhook_config_with_url(self):
        """Test getting global webhook config with URL."""
        mock_manifest = Mock()
        mock_manifest.global_webhook_url = "https://example.com/webhook"
        mock_manifest.global_webhook_token = None

        manager = PushNotificationManager(manifest=mock_manifest)

        config = manager.get_global_webhook_config()

        assert config is not None
        assert config["url"] == "https://example.com/webhook"

    def test_get_effective_webhook_config_task_specific(self):
        """Test getting effective config prefers task-specific."""
        mock_manifest = Mock()
        mock_manifest.global_webhook_url = "https://global.com/webhook"

        manager = PushNotificationManager(manifest=mock_manifest)
        task_id = uuid4()

        manager._push_notification_configs[task_id] = {
            "id": task_id,
            "url": "https://task.com/webhook",
        }

        config = manager.get_effective_webhook_config(task_id)

        assert config is not None
        assert config["url"] == "https://task.com/webhook"

    def test_get_effective_webhook_config_falls_back_to_global(self):
        """Test getting effective config falls back to global."""
        mock_manifest = Mock()
        mock_manifest.global_webhook_url = "https://global.com/webhook"
        mock_manifest.global_webhook_token = None

        manager = PushNotificationManager(manifest=mock_manifest)
        task_id = uuid4()

        config = manager.get_effective_webhook_config(task_id)

        assert config is not None
        assert config["url"] == "https://global.com/webhook"

    @pytest.mark.asyncio
    async def test_initialize_loads_persisted_configs(self):
        """Test initialize loads persisted configs from storage."""
        mock_storage = AsyncMock()
        task_id = uuid4()
        persisted_configs = {
            task_id: {"id": task_id, "url": "https://example.com/webhook"}
        }
        mock_storage.load_all_webhook_configs.return_value = persisted_configs

        manager = PushNotificationManager(storage=mock_storage)
        await manager.initialize()

        assert task_id in manager._push_notification_configs
        assert task_id in manager._notification_sequences

    @pytest.mark.asyncio
    async def test_initialize_handles_load_error(self):
        """Test initialize handles errors when loading configs."""
        mock_storage = AsyncMock()
        mock_storage.load_all_webhook_configs.side_effect = Exception("Load error")

        manager = PushNotificationManager(storage=mock_storage)
        await manager.initialize()

        assert len(manager._push_notification_configs) == 0

    def test_is_push_supported_with_dict_capabilities(self):
        """Test push support check with dict capabilities."""
        mock_manifest = Mock()
        mock_manifest.capabilities = {"push_notifications": True}

        manager = PushNotificationManager(manifest=mock_manifest)

        assert manager.is_push_supported() is True

    def test_is_push_supported_with_object_capabilities(self):
        """Test push support check with object capabilities."""
        mock_manifest = Mock()
        mock_capabilities = Mock()
        mock_capabilities.push_notifications = True
        mock_manifest.capabilities = mock_capabilities

        manager = PushNotificationManager(manifest=mock_manifest)

        assert manager.is_push_supported() is True

    def test_is_push_supported_no_capabilities(self):
        """Test push support check when manifest has no capabilities."""
        mock_manifest = Mock()
        mock_manifest.capabilities = None

        manager = PushNotificationManager(manifest=mock_manifest)

        assert manager.is_push_supported() is False

    def test_get_global_webhook_config_with_token(self):
        """Test getting global webhook config with token."""
        mock_manifest = Mock()
        mock_manifest.global_webhook_url = "https://example.com/webhook"
        mock_manifest.global_webhook_token = "secret-token"

        manager = PushNotificationManager(manifest=mock_manifest)
        config = manager.get_global_webhook_config()

        assert config is not None
        assert config["url"] == "https://example.com/webhook"
        assert config["token"] == "secret-token"

    def test_sanitize_push_config_basic(self):
        """Test sanitizing push config with basic fields."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {
                "id": task_id,
                "url": "https://example.com/webhook",
                "extra_field": "should be removed",
            },
        )

        sanitized = manager._sanitize_push_config(config)

        assert sanitized["id"] == task_id
        assert sanitized["url"] == "https://example.com/webhook"
        assert "extra_field" not in sanitized

    def test_sanitize_push_config_with_token(self):
        """Test sanitizing push config with token."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {
                "id": task_id,
                "url": "https://example.com/webhook",
                "token": "secret",
            },
        )

        sanitized = manager._sanitize_push_config(config)

        assert sanitized["token"] == "secret"

    def test_sanitize_push_config_with_authentication(self):
        """Test sanitizing push config with authentication."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {
                "id": task_id,
                "url": "https://example.com/webhook",
                "authentication": {"type": "bearer"},
            },
        )

        sanitized = manager._sanitize_push_config(config)

        assert sanitized["authentication"] == {"type": "bearer"}

    @pytest.mark.asyncio
    async def test_register_push_config_in_memory(self):
        """Test registering push config in memory only."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )

        await manager.register_push_config(task_id, config, persist=False)

        assert task_id in manager._push_notification_configs
        assert task_id in manager._notification_sequences

    @pytest.mark.asyncio
    async def test_register_push_config_with_storage(self):
        """Test registering push config with storage persistence."""
        mock_storage = AsyncMock()
        manager = PushNotificationManager(storage=mock_storage)
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )

        await manager.register_push_config(task_id, config, persist=True)

        assert task_id in manager._push_notification_configs
        mock_storage.save_webhook_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_push_config_in_memory(self):
        """Test removing push config from memory."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )

        await manager.register_push_config(task_id, config, persist=False)
        removed = await manager.remove_push_config(task_id, delete_from_storage=False)

        assert removed is not None
        assert removed["id"] == task_id
        assert task_id not in manager._push_notification_configs

    @pytest.mark.asyncio
    async def test_remove_push_config_from_storage(self):
        """Test removing push config from storage."""
        mock_storage = AsyncMock()
        manager = PushNotificationManager(storage=mock_storage)
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )

        await manager.register_push_config(task_id, config, persist=True)
        await manager.remove_push_config(task_id, delete_from_storage=True)

        mock_storage.delete_webhook_config.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_remove_push_config_not_found(self):
        """Test removing non-existent push config."""
        manager = PushNotificationManager()
        task_id = uuid4()

        removed = await manager.remove_push_config(task_id)

        assert removed is None

    def test_get_push_config(self):
        """Test getting push config."""
        manager = PushNotificationManager()
        task_id = uuid4()

        result = manager.get_push_config(task_id)
        assert result is None

    def test_build_task_push_config(self):
        """Test building task push config response."""
        manager = PushNotificationManager()
        task_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )
        manager._push_notification_configs[task_id] = config

        result = manager.build_task_push_config(task_id)

        assert result["id"] == task_id
        assert (
            result["push_notification_config"]["url"] == "https://example.com/webhook"
        )

    def test_build_task_push_config_not_found(self):
        """Test building task push config when not found."""
        manager = PushNotificationManager()
        task_id = uuid4()

        with pytest.raises(KeyError, match="No push notification configuration"):
            manager.build_task_push_config(task_id)

    def test_next_sequence(self):
        """Test sequence number generation."""
        manager = PushNotificationManager()
        task_id = uuid4()

        seq1 = manager._next_sequence(task_id)
        seq2 = manager._next_sequence(task_id)

        assert seq1 == 1
        assert seq2 == 2

    def test_build_lifecycle_event(self):
        """Test building lifecycle event."""
        manager = PushNotificationManager()
        task_id = uuid4()
        context_id = uuid4()

        event = manager.build_lifecycle_event(task_id, context_id, "completed", True)

        assert event["kind"] == "status-update"
        assert event["task_id"] == str(task_id)
        assert event["context_id"] == str(context_id)
        assert event["status"]["state"] == "completed"
        assert event["final"] is True
        assert "event_id" in event
        assert "sequence" in event
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_notify_lifecycle_with_config(self):
        """Test lifecycle notification with webhook config."""
        manager = PushNotificationManager()
        task_id = uuid4()
        context_id = uuid4()
        config = cast(
            PushNotificationConfig,
            {"id": task_id, "url": "https://example.com/webhook"},
        )
        manager._push_notification_configs[task_id] = config

        await manager.notify_lifecycle(task_id, context_id, "completed", True)

    @pytest.mark.asyncio
    async def test_notify_lifecycle_without_config(self):
        """Test lifecycle notification without webhook config."""
        manager = PushNotificationManager()
        task_id = uuid4()
        context_id = uuid4()

        await manager.notify_lifecycle(task_id, context_id, "completed", True)

    def test_log_notification_error_with_delivery_error(self):
        """Test logging notification delivery error."""
        from bindu.utils.notifications import NotificationDeliveryError

        manager = PushNotificationManager()
        task_id = uuid4()
        context_id = uuid4()
        error = NotificationDeliveryError(500, "Failed")

        manager._log_notification_error("lifecycle", task_id, context_id, error)

    def test_log_notification_error_with_generic_error(self):
        """Test logging generic notification error."""
        manager = PushNotificationManager()
        task_id = uuid4()
        context_id = uuid4()
        error = Exception("Generic error")

        manager._log_notification_error("artifact", task_id, context_id, error)
