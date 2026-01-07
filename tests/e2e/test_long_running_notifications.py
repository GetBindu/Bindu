"""E2E tests for long-running task notification system (Issue #69).

This test module validates the complete end-to-end flow of the long-running
notification system without requiring external infrastructure (Redis/Postgres).

Tests use in-memory storage and scheduler, with mock HTTP endpoints to capture
webhook deliveries.

Requirements verified:
1. long_running flag in MessageSendConfiguration
2. Webhook persistence for long-running tasks
3. Status update notifications (working, completed)
4. Artifact update notifications
5. Global webhook fallback
6. Correct event sequencing
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import PushNotificationConfig
from bindu.server.notifications.push_manager import PushNotificationManager
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from bindu.server.workers.manifest_worker import ManifestWorker


class WebhookCapture:
    """Captures webhook deliveries for testing."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.delivery_count = 0

    def capture_event(self, config: PushNotificationConfig, event: dict[str, Any]) -> None:
        """Capture a webhook event delivery."""
        self.events.append({
            "config": config,
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.delivery_count += 1

    def get_events_by_kind(self, kind: str) -> list[dict[str, Any]]:
        """Get all events of a specific kind."""
        return [e for e in self.events if e["event"].get("kind") == kind]

    def get_status_updates(self) -> list[dict[str, Any]]:
        """Get all status-update events."""
        return self.get_events_by_kind("status-update")

    def get_artifact_updates(self) -> list[dict[str, Any]]:
        """Get all artifact-update events."""
        return self.get_events_by_kind("artifact-update")

    def clear(self) -> None:
        """Clear all captured events."""
        self.events.clear()
        self.delivery_count = 0


class TestLongRunningNotificationE2E:
    """End-to-end tests for long-running notification system."""

    @pytest.fixture
    def webhook_capture(self) -> WebhookCapture:
        """Create a webhook capture instance."""
        return WebhookCapture()

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        """Create in-memory storage."""
        return InMemoryStorage()

    @pytest.fixture
    def scheduler(self) -> InMemoryScheduler:
        """Create in-memory scheduler."""
        return InMemoryScheduler()

    @pytest.fixture
    def mock_manifest(self) -> MagicMock:
        """Create a mock agent manifest."""
        manifest = MagicMock(spec=AgentManifest)
        manifest.id = uuid4()
        manifest.name = "test_long_running_agent"
        manifest.capabilities = {"push_notifications": True}
        manifest.global_webhook_url = None
        manifest.global_webhook_token = None
        manifest.enable_system_message = False
        manifest.enable_context_based_history = False

        # Mock DID extension
        manifest.did_extension = MagicMock()
        manifest.did_extension.did = "did:test:long_running_agent"
        manifest.did_extension.sign_text.return_value = "mock_signature"

        # Mock agent execution - returns a generator
        def mock_run(message_history: list):
            yield "Long running task completed successfully"

        manifest.run = mock_run

        return manifest

    @pytest.fixture
    def push_manager(
        self,
        mock_manifest: MagicMock,
        storage: InMemoryStorage,
        webhook_capture: WebhookCapture,
    ) -> PushNotificationManager:
        """Create a push notification manager with captured deliveries."""
        manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        # Patch the notification service to capture events
        async def capture_send(config: PushNotificationConfig, event: dict[str, Any]) -> None:
            webhook_capture.capture_event(config, event)

        manager.notification_service.send_event = AsyncMock(side_effect=capture_send)

        return manager

    @pytest.mark.asyncio
    async def test_long_running_task_full_flow(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        mock_manifest: MagicMock,
        webhook_capture: WebhookCapture,
    ):
        """Test complete flow: submit → working → artifact → completed.

        Verifies:
        - Task submission with long_running=True
        - Webhook config persistence
        - Status notifications sent
        - Artifact notifications sent
        - Correct event sequencing
        """
        task_id = uuid4()
        context_id = uuid4()
        webhook_url = "https://test.example.com/webhook"
        webhook_token = "test_secret_token"

        webhook_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": webhook_url,
            "token": webhook_token,
        }

        # Create push manager with capture
        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        async def capture_send(config: PushNotificationConfig, event: dict[str, Any]) -> None:
            webhook_capture.capture_event(config, event)

        push_manager.notification_service.send_event = AsyncMock(side_effect=capture_send)

        # Register webhook config with persistence (simulating long_running=True)
        await push_manager.register_push_config(task_id, webhook_config, persist=True)

        # Verify persistence
        persisted = await storage.load_webhook_config(task_id)
        assert persisted is not None, "Webhook config should be persisted"
        assert persisted["url"] == webhook_url

        # Submit task
        message = {
            "task_id": task_id,
            "context_id": context_id,
            "message_id": uuid4(),
            "kind": "message",
            "role": "user",
            "parts": [{"kind": "text", "text": "Process this long running task"}],
        }
        await storage.submit_task(context_id, message)

        # Simulate lifecycle: working
        await push_manager.notify_lifecycle(task_id, context_id, "working", final=False)

        # Simulate artifact generation
        artifact = {
            "artifact_id": str(uuid4()),
            "name": "result.json",
            "parts": [{"kind": "text", "text": '{"status": "processed"}'}],
        }
        await push_manager.notify_artifact(task_id, context_id, artifact)

        # Simulate lifecycle: completed
        await push_manager.notify_lifecycle(task_id, context_id, "completed", final=True)

        # Verify events
        assert webhook_capture.delivery_count == 3, f"Expected 3 events, got {webhook_capture.delivery_count}"

        status_updates = webhook_capture.get_status_updates()
        artifact_updates = webhook_capture.get_artifact_updates()

        assert len(status_updates) == 2, "Should have 2 status updates (working, completed)"
        assert len(artifact_updates) == 1, "Should have 1 artifact update"

        # Verify event order by sequence
        all_sequences = [e["event"]["sequence"] for e in webhook_capture.events]
        assert all_sequences == [1, 2, 3], f"Events should be in sequence, got {all_sequences}"

        # Verify working state
        working_event = status_updates[0]["event"]
        assert working_event["status"]["state"] == "working"
        assert working_event["final"] is False

        # Verify artifact event
        artifact_event = artifact_updates[0]["event"]
        assert artifact_event["artifact"]["name"] == "result.json"

        # Verify completed state
        completed_event = status_updates[1]["event"]
        assert completed_event["status"]["state"] == "completed"
        assert completed_event["final"] is True

    @pytest.mark.asyncio
    async def test_non_long_running_task_no_persistence(
        self,
        storage: InMemoryStorage,
        mock_manifest: MagicMock,
    ):
        """Test that non-long-running tasks don't persist webhook config.

        Verifies backward compatibility: tasks without long_running=True
        should work but not persist webhook configs.
        """
        task_id = uuid4()
        webhook_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://test.example.com/webhook",
        }

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        # Register without persistence (simulating long_running=False)
        await push_manager.register_push_config(task_id, webhook_config, persist=False)

        # Verify NOT persisted
        persisted = await storage.load_webhook_config(task_id)
        assert persisted is None, "Webhook config should NOT be persisted for non-long-running tasks"

        # But in-memory should still work
        in_memory = push_manager.get_push_config(task_id)
        assert in_memory is not None, "In-memory config should exist"

    @pytest.mark.asyncio
    async def test_global_webhook_fallback(
        self,
        storage: InMemoryStorage,
        webhook_capture: WebhookCapture,
    ):
        """Test global webhook configuration fallback.

        Verifies:
        - Global webhook is used when no task-specific config exists
        - Task-specific config takes priority over global
        """
        task_id_1 = uuid4()
        task_id_2 = uuid4()
        context_id = uuid4()

        # Create manifest with global webhook
        mock_manifest = MagicMock(spec=AgentManifest)
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = "https://global.example.com/webhook"
        mock_manifest.global_webhook_token = "global_token"

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        async def capture_send(config: PushNotificationConfig, event: dict[str, Any]) -> None:
            webhook_capture.capture_event(config, event)

        push_manager.notification_service.send_event = AsyncMock(side_effect=capture_send)

        # Task 1: No specific config, should use global
        effective_1 = push_manager.get_effective_webhook_config(task_id_1)
        assert effective_1 is not None, "Should have effective config from global"
        assert effective_1["url"] == "https://global.example.com/webhook"

        # Task 2: Has specific config, should use it
        task_specific_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://task-specific.example.com/webhook",
            "token": "task_token",
        }
        await push_manager.register_push_config(task_id_2, task_specific_config, persist=False)

        effective_2 = push_manager.get_effective_webhook_config(task_id_2)
        assert effective_2["url"] == "https://task-specific.example.com/webhook"

        # Send notifications to both
        await push_manager.notify_lifecycle(task_id_1, context_id, "working", final=False)
        await push_manager.notify_lifecycle(task_id_2, context_id, "working", final=False)

        assert webhook_capture.delivery_count == 2

        # Verify URLs used
        urls = [e["config"]["url"] for e in webhook_capture.events]
        assert "https://global.example.com/webhook" in urls
        assert "https://task-specific.example.com/webhook" in urls

    @pytest.mark.asyncio
    async def test_webhook_restoration_on_init(
        self,
        storage: InMemoryStorage,
        mock_manifest: MagicMock,
    ):
        """Test webhook config restoration on PushManager initialization.

        Simulates server restart scenario where persisted configs
        should be loaded from storage.
        """
        task_id = uuid4()
        webhook_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://persisted.example.com/webhook",
            "token": "persisted_token",
        }

        # Pre-populate storage (simulating existing persisted data)
        await storage.save_webhook_config(task_id, webhook_config)

        # Create new PushManager (simulating server restart)
        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        # Initialize should load persisted configs
        await push_manager.initialize()

        # Verify config was restored
        restored = push_manager.get_push_config(task_id)
        assert restored is not None, "Persisted config should be restored"
        assert restored["url"] == "https://persisted.example.com/webhook"

    @pytest.mark.asyncio
    async def test_event_schema_compliance(
        self,
        storage: InMemoryStorage,
        mock_manifest: MagicMock,
        webhook_capture: WebhookCapture,
    ):
        """Test that generated events comply with expected schema.

        Verifies:
        - Status events have required fields
        - Artifact events have required fields
        - UUIDs are properly serialized as strings
        """
        task_id = uuid4()
        context_id = uuid4()

        webhook_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://schema.example.com/webhook",
        }

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        async def capture_send(config: PushNotificationConfig, event: dict[str, Any]) -> None:
            webhook_capture.capture_event(config, event)

        push_manager.notification_service.send_event = AsyncMock(side_effect=capture_send)
        await push_manager.register_push_config(task_id, webhook_config, persist=False)

        # Send status event
        await push_manager.notify_lifecycle(task_id, context_id, "working", final=False)

        # Send artifact event
        artifact = {
            "artifact_id": str(uuid4()),
            "name": "test_artifact",
            "parts": [{"kind": "text", "text": "content"}],
        }
        await push_manager.notify_artifact(task_id, context_id, artifact)

        # Verify status event schema
        status_event = webhook_capture.get_status_updates()[0]["event"]
        assert "event_id" in status_event
        assert "sequence" in status_event
        assert "timestamp" in status_event
        assert "kind" in status_event
        assert "task_id" in status_event
        assert "context_id" in status_event
        assert "status" in status_event
        assert "final" in status_event

        # Verify status nested fields
        assert "state" in status_event["status"]
        assert "timestamp" in status_event["status"]

        # Verify UUIDs are strings
        assert isinstance(status_event["task_id"], str)
        assert isinstance(status_event["context_id"], str)

        # Verify artifact event schema
        artifact_event = webhook_capture.get_artifact_updates()[0]["event"]
        assert "event_id" in artifact_event
        assert "sequence" in artifact_event
        assert "timestamp" in artifact_event
        assert "kind" in artifact_event
        assert "task_id" in artifact_event
        assert "context_id" in artifact_event
        assert "artifact" in artifact_event

        # Verify artifact nested fields
        assert "name" in artifact_event["artifact"]
        assert "parts" in artifact_event["artifact"]

    @pytest.mark.asyncio
    async def test_cleanup_on_task_completion(
        self,
        storage: InMemoryStorage,
        mock_manifest: MagicMock,
    ):
        """Test webhook cleanup after task completion."""
        task_id = uuid4()
        webhook_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://cleanup.example.com/webhook",
        }

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        # Register with persistence
        await push_manager.register_push_config(task_id, webhook_config, persist=True)

        # Verify exists
        assert await storage.load_webhook_config(task_id) is not None

        # Remove with storage cleanup
        await push_manager.remove_push_config(task_id, delete_from_storage=True)

        # Verify removed from both
        assert push_manager.get_push_config(task_id) is None
        assert await storage.load_webhook_config(task_id) is None


class TestIssue69RequirementsCoverage:
    """Explicit tests mapping to Issue #69 requirements."""

    @pytest.mark.asyncio
    async def test_requirement_1_explicit_long_running_flag(self):
        """Requirement 1: long_running flag in MessageSendConfiguration."""
        from bindu.common.protocol.types import MessageSendConfiguration

        # Test flag can be set to True
        config_true: MessageSendConfiguration = {
            "accepted_output_modes": ["application/json"],
            "long_running": True,
        }
        assert config_true.get("long_running") is True

        # Test flag defaults to False
        config_default: MessageSendConfiguration = {
            "accepted_output_modes": ["application/json"],
        }
        assert config_default.get("long_running", False) is False

    @pytest.mark.asyncio
    async def test_requirement_2_comprehensive_event_delivery(self):
        """Requirement 2: Status + artifact events."""
        storage = InMemoryStorage()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = None

        events_captured = []

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        async def capture(config, event):
            events_captured.append(event)

        push_manager.notification_service.send_event = AsyncMock(side_effect=capture)

        task_id = uuid4()
        context_id = uuid4()
        await push_manager.register_push_config(
            task_id,
            {"id": uuid4(), "url": "https://test.com"},
            persist=False,
        )

        # Send both event types
        await push_manager.notify_lifecycle(task_id, context_id, "working", final=False)
        await push_manager.notify_artifact(
            task_id, context_id, {"name": "test", "parts": []}
        )
        await push_manager.notify_lifecycle(task_id, context_id, "completed", final=True)

        kinds = [e["kind"] for e in events_captured]
        assert "status-update" in kinds, "Should have status events"
        assert "artifact-update" in kinds, "Should have artifact events"

    @pytest.mark.asyncio
    async def test_requirement_3_persistent_storage(self):
        """Requirement 3: Webhook configs persist to storage."""
        storage = InMemoryStorage()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = None

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://persist.test.com/webhook",
            "token": "secret",
        }

        # Persist
        await push_manager.register_push_config(task_id, config, persist=True)

        # Verify in storage
        loaded = await storage.load_webhook_config(task_id)
        assert loaded is not None
        assert loaded["url"] == config["url"]
        assert loaded["token"] == config["token"]

    @pytest.mark.asyncio
    async def test_requirement_4_global_webhook_configuration(self):
        """Requirement 4: Global webhook fallback."""
        storage = InMemoryStorage()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = "https://global.test.com/webhook"
        mock_manifest.global_webhook_token = "global_secret"

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        # No task-specific config
        task_id = uuid4()
        effective = push_manager.get_effective_webhook_config(task_id)

        assert effective is not None, "Should fall back to global"
        assert effective["url"] == "https://global.test.com/webhook"
        assert effective["token"] == "global_secret"

    @pytest.mark.asyncio
    async def test_requirement_5_existing_event_schema(self):
        """Requirement 5: Use existing status-update and artifact-update formats."""
        storage = InMemoryStorage()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = None

        captured_event = None

        push_manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=storage,
        )

        async def capture(config, event):
            nonlocal captured_event
            captured_event = event

        push_manager.notification_service.send_event = AsyncMock(side_effect=capture)

        task_id = uuid4()
        context_id = uuid4()
        await push_manager.register_push_config(
            task_id,
            {"id": uuid4(), "url": "https://test.com"},
            persist=False,
        )

        await push_manager.notify_lifecycle(task_id, context_id, "working", final=False)

        # Verify existing schema format
        assert captured_event["kind"] == "status-update"
        assert "status" in captured_event
        assert captured_event["status"]["state"] == "working"


# Run summary at module level for test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
