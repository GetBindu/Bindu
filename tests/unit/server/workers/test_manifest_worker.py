"""Minimal tests for ManifestWorker."""

from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest

from bindu.common.protocol.types import Task, TaskSendParams
from bindu.server.workers.manifest_worker import ManifestWorker


class TestManifestWorker:
    """Test ManifestWorker functionality."""

    def test_build_message_history_delegates_to_converter(self):
        """Test building message history delegates to MessageConverter."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # The method delegates to MessageConverter.to_chat_format
        result = worker.build_message_history(messages)  # type: ignore[arg-type]

        # Result type depends on MessageConverter implementation
        assert isinstance(result, list)

    def test_build_artifacts(self):
        """Test building artifacts from result."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        result = "Task completed successfully"

        artifacts = worker.build_artifacts(result)

        assert len(artifacts) > 0
        assert "parts" in artifacts[0]

    @pytest.mark.asyncio
    async def test_handle_task_failure(self):
        """Test handling task failure."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task = cast(
            Task,
            {
                "id": uuid4(),
                "context_id": uuid4(),
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        await worker._handle_task_failure(task, "Test error")

        mock_storage.update_task.assert_called_once()
        call_args = mock_storage.update_task.call_args
        assert call_args[0][0] == task["id"]
        assert call_args[1]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_notify_lifecycle_with_callback(self):
        """Test lifecycle notification with callback."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_callback = Mock()

        worker = ManifestWorker(
            manifest=mock_manifest,
            scheduler=mock_scheduler,
            storage=mock_storage,
            lifecycle_notifier=mock_callback,
        )

        task_id = uuid4()
        context_id = uuid4()

        await worker._notify_lifecycle(task_id, context_id, "completed", True)

        mock_callback.assert_called_once_with(task_id, context_id, "completed", True)

    @pytest.mark.asyncio
    async def test_notify_lifecycle_without_callback(self):
        """Test lifecycle notification without callback."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        context_id = uuid4()

        # Should not raise error
        await worker._notify_lifecycle(task_id, context_id, "completed", True)

    @pytest.mark.asyncio
    async def test_settle_payment_handles_missing_context(self):
        """Test payment settlement with missing context returns error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        # Empty payment context should return error
        payment_context = {}

        result = await worker._settle_payment(payment_context)

        # Should return error status
        assert "x402_status" in result or "error" in str(result).lower()

    def test_add_state_change_event(self):
        """Test adding state change event."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        # Should not raise error
        worker._add_state_change_event("working", "pending")

    def test_log_notification_error(self):
        """Test logging notification error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        context_id = uuid4()
        error = Exception("Test error")

        # Should not raise error
        worker._log_notification_error("Artifact", task_id, context_id, error)

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test canceling a task."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
        }
        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker.cancel_task({"task_id": task_id})

        mock_storage.update_task.assert_called_once_with(task_id, state="canceled")

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test canceling a task that doesn't exist."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        await worker.cancel_task({"task_id": task_id})

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_complete_message_history_with_references(self):
        """Test building message history with reference task IDs."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        ref_task_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [
                    {
                        "role": "user",
                        "content": "test",
                        "reference_task_ids": [ref_task_id],
                    }
                ],
            },
        )

        ref_task = {
            "id": ref_task_id,
            "context_id": context_id,
            "history": [{"role": "user", "content": "previous"}],
        }

        mock_storage.load_task.return_value = ref_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)
        mock_storage.load_task.assert_called()

    @pytest.mark.asyncio
    async def test_build_complete_message_history_without_references(self):
        """Test building message history without reference task IDs."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [{"role": "user", "content": "test"}],
            },
        )

        mock_storage.load_context_tasks.return_value = [task]

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_settle_payment_with_valid_context(self):
        """Test payment settlement with valid payment context."""
        mock_manifest = Mock()
        mock_manifest.x402_extension = Mock()
        mock_manifest.x402_extension.facilitator_config = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        payment_context = {"session_id": "sess123", "amount": "100", "token": "USDC"}

        result = await worker._settle_payment(payment_context)

        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_intermediate_state(self):
        """Test handling intermediate task state."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_intermediate_state(
            task, "input-required", "Please provide input"
        )

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_handle_terminal_state(self):
        """Test handling terminal task state."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_terminal_state(task, "Task completed", "completed")

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_handle_terminal_state_with_payment(self):
        """Test handling terminal state with payment settlement."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.x402_extension = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        payment_context = {"session_id": "sess123"}

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_terminal_state(
            task, "Task completed", "completed", payment_context=payment_context
        )

        mock_storage.update_task.assert_called()

    def test_add_state_change_event_with_error(self):
        """Test adding state change event with error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        worker._add_state_change_event("failed", "working", error="Test error")

    def test_add_state_change_event_without_from_state(self):
        """Test adding state change event without from_state."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        worker._add_state_change_event("completed")

    @pytest.mark.asyncio
    async def test_run_task_basic_flow(self):
        """Test basic task execution flow."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()
        mock_manifest.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_with_input_required_response(self):
        """Test task execution with input-required response."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(
            return_value='{"state": "input-required", "prompt": "Need more info"}'
        )
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_with_auth_required_response(self):
        """Test task execution with auth-required response."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(
            return_value='{"state": "auth-required", "prompt": "Login needed"}'
        )
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_with_payment_context(self):
        """Test task execution with payment context."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False
        mock_manifest.x402_extension = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(
            TaskSendParams,
            {
                "task_id": task_id,
                "context_id": context_id,
                "payment_context": {"session_id": "sess123"},
            },
        )

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_not_found(self):
        """Test task execution when task doesn't exist."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": uuid4(), "context_id": uuid4()})

        with pytest.raises(ValueError, match="not found"):
            await worker.run_task(params)

    @pytest.mark.asyncio
    async def test_run_task_with_agent_error(self):
        """Test task execution when agent raises error."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(side_effect=Exception("Agent error"))
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        with pytest.raises(Exception, match="Agent error"):
            await worker.run_task(params)

        # Should have updated task to failed state
        assert any(
            call[1].get("state") == "failed"
            for call in mock_storage.update_task.call_args_list
        )

    @pytest.mark.asyncio
    async def test_run_task_with_system_message(self):
        """Test task execution with system message enabled."""
        from unittest.mock import patch

        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = True
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        with patch(
            "bindu.server.workers.manifest_worker.app_settings"
        ) as mock_settings:
            mock_settings.agent.enable_structured_responses = True
            mock_settings.agent.structured_response_system_prompt = "System prompt"
            mock_settings.agent.terminal_states = frozenset(
                ["completed", "failed", "canceled"]
            )

            await worker.run_task(params)

        mock_manifest.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_with_context_based_history(self):
        """Test task execution with context-based history."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = True

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        prev_task_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "current"}],
        }

        prev_task = {
            "id": prev_task_id,
            "context_id": context_id,
            "history": [{"role": "user", "content": "previous"}],
        }

        mock_storage.load_task.return_value = mock_task
        mock_storage.list_tasks_by_context.return_value = [prev_task, mock_task]

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.list_tasks_by_context.assert_called_once_with(context_id)

    @pytest.mark.asyncio
    async def test_settle_payment_with_facilitator(self):
        """Test payment settlement with facilitator client."""
        from unittest.mock import patch

        mock_manifest = Mock()
        mock_manifest.x402_extension = Mock()
        mock_manifest.x402_extension.facilitator_config = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        payment_context = {"session_id": "sess123", "amount": "100", "token": "USDC"}

        with patch(
            "bindu.server.workers.manifest_worker.FacilitatorClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.settle_payment = AsyncMock(return_value={"status": "success"})
            mock_client_class.return_value = mock_client

            result = await worker._settle_payment(payment_context)

            assert result is not None

    @pytest.mark.asyncio
    async def test_build_complete_message_history_with_context_disabled(self):
        """Test building message history with context-based history disabled."""
        mock_manifest = Mock()
        mock_manifest.enable_context_based_history = False
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [{"role": "user", "content": "test"}],
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)
        # Should not call list_tasks_by_context when disabled
        mock_storage.list_tasks_by_context.assert_not_called()
