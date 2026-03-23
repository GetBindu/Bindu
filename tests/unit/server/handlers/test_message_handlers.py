"""Minimal tests for message handler utilities."""

from unittest.mock import AsyncMock, Mock
import pytest
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from bindu.common.protocol.types import Task
from bindu.server.handlers.message_handlers import MessageHandlers


class TestMessageHandlers:
    """Test message handler functionality."""

    @pytest.mark.asyncio
    async def test_handle_stream_error_loads_task(self):
        """Test stream error handler loads task."""
        mock_storage = AsyncMock()
        mock_task = {
            "id": "task123",
            "status": {
                "state": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.load_task.return_value = mock_task

        handler = MessageHandlers(scheduler=Mock(), storage=mock_storage)

        task = cast(Task, {"id": "task123"})
        error = Exception("Test error")
        terminal_states = frozenset(["completed", "failed", "canceled"])

        result = await handler._handle_stream_error(
            task,
            "ctx1",
            error,
            terminal_states,
        )

        assert "kind" in result
        assert result["kind"] == "status-update"
        assert result["task_id"] == "task123"
        mock_storage.load_task.assert_called()

    @pytest.mark.asyncio
    async def test_handle_stream_error_updates_failed_state(self):
        """Test stream error handler updates task to failed."""
        mock_storage = AsyncMock()
        mock_task = {
            "id": "task123",
            "status": {
                "state": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        updated_task = {
            "id": "task123",
            "status": {
                "state": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.load_task.return_value = mock_task
        mock_storage.update_task.return_value = updated_task

        handler = MessageHandlers(scheduler=Mock(), storage=mock_storage)

        task = cast(Task, {"id": "task123"})
        error = Exception("Test error")
        terminal_states = frozenset(["completed", "failed", "canceled"])

        result = await handler._handle_stream_error(
            task, "ctx1", error, terminal_states
        )

        assert result["status"]["state"] == "failed"
        assert result["final"] is True
        mock_storage.update_task.assert_called_once_with("task123", state="failed")

    @pytest.mark.asyncio
    async def test_handle_stream_error_handles_load_failure(self):
        """Test stream error handler when task load fails."""
        mock_storage = AsyncMock()
        mock_storage.load_task.side_effect = Exception("Load failed")

        handler = MessageHandlers(scheduler=Mock(), storage=mock_storage)

        task = cast(Task, {"id": "task123"})
        error = Exception("Test error")
        terminal_states = frozenset(["completed", "failed", "canceled"])

        result = await handler._handle_stream_error(
            task, "ctx1", error, terminal_states
        )

        assert "kind" in result
        assert result["status"]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_submit_and_schedule_task_basic(self):
        """Test basic task submission and scheduling."""
        mock_storage = AsyncMock()
        mock_scheduler = AsyncMock()
        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        request_params = {"message": {"content": "test", "context_id": str(context_id)}}

        result_task, result_ctx = await handler._submit_and_schedule_task(
            request_params
        )

        assert result_task["id"] == task_id
        assert result_ctx == context_id
        mock_storage.submit_task.assert_called_once()
        mock_scheduler.run_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_and_schedule_task_with_history_length(self):
        """Test task submission with history_length config."""
        mock_storage = AsyncMock()
        mock_scheduler = AsyncMock()
        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        request_params = {
            "message": {"content": "test", "context_id": str(context_id)},
            "configuration": {"history_length": 10},
        }

        await handler._submit_and_schedule_task(request_params)

        call_args = mock_scheduler.run_task.call_args[0][0]
        assert call_args["history_length"] == 10

    @pytest.mark.asyncio
    async def test_submit_and_schedule_task_with_push_config(self):
        """Test task submission with push notification config."""
        mock_storage = AsyncMock()
        mock_scheduler = AsyncMock()
        mock_push_manager = AsyncMock()
        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
            push_manager=mock_push_manager,
        )

        push_config = {"url": "https://example.com/webhook"}
        request_params = {
            "message": {"content": "test", "context_id": str(context_id)},
            "configuration": {
                "push_notification_config": push_config,
                "long_running": True,
            },
        }

        await handler._submit_and_schedule_task(request_params)

        mock_push_manager.register_push_config.assert_called_once_with(
            task_id, push_config, persist=True
        )

    @pytest.mark.asyncio
    async def test_submit_and_schedule_task_with_payment_context(self):
        """Test task submission with payment context in metadata."""
        mock_storage = AsyncMock()
        mock_scheduler = AsyncMock()
        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        payment_ctx = {"session_id": "sess123"}
        request_params = {
            "message": {
                "content": "test",
                "context_id": str(context_id),
                "metadata": {"_payment_context": payment_ctx},
            }
        }

        await handler._submit_and_schedule_task(request_params)

        call_args = mock_scheduler.run_task.call_args[0][0]
        assert call_args["payment_context"] == payment_ctx

    def test_to_jsonable_uuid(self):
        """Test UUID conversion to string."""
        test_uuid = uuid4()
        result = MessageHandlers._to_jsonable(test_uuid)
        assert result == str(test_uuid)

    def test_to_jsonable_dict(self):
        """Test dict with UUID values."""
        test_uuid = uuid4()
        data = {"id": test_uuid, "name": "test"}
        result = MessageHandlers._to_jsonable(data)
        assert result["id"] == str(test_uuid)
        assert result["name"] == "test"

    def test_to_jsonable_list(self):
        """Test list with UUID values."""
        test_uuid = uuid4()
        data = [test_uuid, "test", 123]
        result = MessageHandlers._to_jsonable(data)
        assert result[0] == str(test_uuid)
        assert result[1] == "test"
        assert result[2] == 123

    def test_to_jsonable_nested(self):
        """Test nested structures with UUIDs."""
        test_uuid = uuid4()
        data = {"items": [{"id": test_uuid}]}
        result = MessageHandlers._to_jsonable(data)
        assert result["items"][0]["id"] == str(test_uuid)

    def test_sse_event_formatting(self):
        """Test SSE event formatting."""
        payload = {"kind": "status-update", "task_id": "123"}
        result = MessageHandlers._sse_event(payload)
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        assert "status-update" in result

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test send_message RPC method."""
        mock_storage = AsyncMock()
        mock_scheduler = AsyncMock()
        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "pending",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        request = {
            "jsonrpc": "2.0",
            "id": "req1",
            "params": {"message": {"content": "test", "context_id": str(context_id)}},
        }

        response = await handler.send_message(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req1"
        assert response["result"]["id"] == task_id

    @pytest.mark.asyncio
    async def test_send_message_rpc(self):
        """Test send_message RPC method."""
        mock_scheduler = AsyncMock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "pending", "timestamp": "2024-01-01T00:00:00Z"},
        }
        mock_storage.submit_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        request = {
            "jsonrpc": "2.0",
            "id": "req1",
            "params": {"message": {"content": "test", "context_id": str(context_id)}},
        }

        response = await handler.send_message(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "req1"
        assert "result" in response

    @pytest.mark.asyncio
    async def test_stream_message_basic(self):
        """Test stream_message basic functionality."""
        mock_scheduler = AsyncMock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "completed", "timestamp": "2024-01-01T00:00:00Z"},
            "artifacts": [{"type": "text", "content": "result"}],
        }
        mock_storage.submit_task.return_value = mock_task
        mock_storage.load_task.return_value = mock_task

        handler = MessageHandlers(
            scheduler=mock_scheduler,
            storage=mock_storage,
            context_id_parser=lambda x: context_id,
        )

        request = {
            "jsonrpc": "2.0",
            "id": "req1",
            "params": {"message": {"content": "test", "context_id": str(context_id)}},
        }

        response = handler.stream_message(request)

        assert response is not None
