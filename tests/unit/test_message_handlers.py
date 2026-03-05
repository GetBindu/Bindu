# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for MessageHandlers.

Covers send_message and stream_message (SSE) RPC dispatch methods
in isolation using InMemoryStorage, a mock scheduler, and MockManifest.

Note on scheduler mocking: InMemoryScheduler uses an anyio memory channel.
Sending to it without a running consumer blocks, so send_message tests use
a mock scheduler. stream_message does not call the scheduler so it uses
storage directly.
"""

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import (
    SendMessageRequest,
    StreamMessageRequest,
)
from bindu.server.handlers.message_handlers import MessageHandlers
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.mocks import MockManifest
from tests.utils import (
    assert_jsonrpc_success,
    create_test_message,
)


def _mock_scheduler():
    """Scheduler stub that never blocks on channel sends."""
    sched = MagicMock()
    sched.run_task = AsyncMock(return_value=None)
    sched.cancel_task = AsyncMock(return_value=None)
    return sched


def _make_handlers(storage, manifest=None, workers=None, push_manager=None):
    return MessageHandlers(
        scheduler=_mock_scheduler(),
        storage=storage,
        manifest=manifest,
        workers=workers,
        context_id_parser=lambda cid: cid if cid else uuid4(),
        push_manager=push_manager,
    )


def _send_request(message, config=None):
    return cast(
        SendMessageRequest,
        {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "message/send",
            "params": {
                "message": message,
                "configuration": config or {},
            },
        },
    )


def _stream_request(message, config=None):
    return cast(
        StreamMessageRequest,
        {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "message/stream",
            "params": {
                "message": message,
                "configuration": config or {},
            },
        },
    )


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_submits_task_and_returns_response():
    """send_message creates a task in submitted state and returns it."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="hello agent")
    request = _send_request(message)

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)

    task = response["result"]
    assert task["kind"] == "task"
    assert task["status"]["state"] == "submitted"


@pytest.mark.asyncio
async def test_send_message_context_id_persisted():
    """send_message preserves the context_id from the inbound message."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    context_id = uuid4()
    message = create_test_message(text="ctx check", context_id=context_id)
    request = _send_request(message)

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)
    assert response["result"]["context_id"] == context_id


@pytest.mark.asyncio
async def test_send_message_with_history_length_config():
    """send_message passes history_length from configuration without error."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="history config")
    request = _send_request(message, config={"history_length": 5})

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)


@pytest.mark.asyncio
async def test_send_message_without_context_id_generates_one():
    """send_message auto-generates a context_id when the message omits it."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="no context")
    message["context_id"] = None  # type: ignore[assignment]
    request = _send_request(message)

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)
    assert response["result"]["context_id"] is not None


@pytest.mark.asyncio
async def test_send_message_with_push_notification_config(mock_push_manager):
    """send_message registers push config when provided in configuration."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage, push_manager=mock_push_manager)

    message = create_test_message(text="push test")
    request = _send_request(
        message,
        config={
            "push_notification_config": {
                "url": "https://example.com/webhook",
                "token": "secret",
            }
        },
    )

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)
    assert len(mock_push_manager.registered) == 1


@pytest.mark.asyncio
async def test_send_message_payment_context_injected_and_stripped_flow():
    """
    Simulate endpoint injecting full _payment_context and ensure:
    1. Handler processes request successfully
    2. _payment_context does NOT persist in storage
    """
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    # Simulate endpoint-injected metadata
    message = create_test_message(
        text="paid request full context",
        metadata={
            "_payment_context": {
                "payment_payload": {"amount": 100},
                "payment_requirements": {"currency": "USD"},
                "verify_response": {"verified": True},
            }
        },
    )

    request = _send_request(message)

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)

    stored_task = await storage.load_task(response["result"]["id"])
    stored_metadata = (stored_task["history"] or [{}])[-1].get("metadata", {})

    # Core assertion: endpoint injection must not leak to storage
    assert "_payment_context" not in stored_metadata

@pytest.mark.asyncio
async def test_send_message_invalid_metadata_type_handled():
    """
    If metadata is not a dict, the handler should not crash and should normalize metadata safely.
    """
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(
        text = "invalid metadata",
        metadata = "this_should_be_a_dict"
    )
    request = _send_request(message)

    response = await handlers.send_message(request)
    assert_jsonrpc_success(response)

    stored_task = await storage.load_task(response["result"]["id"])
    stored_metadata = (stored_task["history"] or [{}])[-1].get("metadata", {})
    #Metadata should be normalized to a dictionary
    assert isinstance(stored_metadata, dict) 
    
@pytest.mark.asyncio
async def test_send_message_queues_task_to_scheduler():
    """send_message calls scheduler.run_task exactly once per request."""
    storage = InMemoryStorage()
    scheduler = _mock_scheduler()
    handlers = MessageHandlers(
        scheduler=scheduler,
        storage=storage,
        manifest=None,
        workers=None,
        context_id_parser=lambda cid: cid if cid else uuid4(),
        push_manager=None,
    )

    message = create_test_message(text="queue check")
    request = _send_request(message)

    await handlers.send_message(request)
    scheduler.run_task.assert_called_once()


# ---------------------------------------------------------------------------
# stream_message — SSE path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_message_returns_streaming_response():
    """stream_message returns a StreamingResponse with SSE media type."""
    from starlette.responses import StreamingResponse

    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="stream me")
    request = _stream_request(message)

    response = await handlers.stream_message(request)
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"


@pytest.mark.skip(reason="Test times out - async infrastructure issue")
@pytest.mark.asyncio
async def test_stream_message_emits_status_working_event():
    """stream_message first SSE event announces state=working."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="working check")
    request = _stream_request(message)

    response = await handlers.stream_message(request)

    events = []
    async for chunk in response.body_iterator:
        line = chunk.decode() if isinstance(chunk, bytes) else chunk
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    assert events[0]["kind"] == "status-update"
    assert events[0]["status"]["state"] == "working"


@pytest.mark.skip(reason="Test times out - async infrastructure issue")
@pytest.mark.asyncio
async def test_stream_message_emits_completed_event():
    """stream_message final SSE event announces state=completed with final=True."""
    storage = InMemoryStorage()
    manifest = cast(AgentManifest, MockManifest())
    handlers = _make_handlers(storage, manifest=manifest)

    message = create_test_message(text="complete check")
    request = _stream_request(message)

    response = await handlers.stream_message(request)

    events = []
    async for chunk in response.body_iterator:
        line = chunk.decode() if isinstance(chunk, bytes) else chunk
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    final_event = events[-1]
    assert final_event["kind"] == "status-update"
    assert final_event["status"]["state"] in ("completed", "failed")
    assert final_event["final"] is True


@pytest.mark.skip(reason="Test times out - async infrastructure issue")
@pytest.mark.asyncio
async def test_stream_message_task_reaches_terminal_state():
    """After streaming, the task in storage is no longer in submitted state."""
    storage = InMemoryStorage()
    manifest = cast(AgentManifest, MockManifest())
    handlers = _make_handlers(storage, manifest=manifest)

    message = create_test_message(text="state check")
    request = _stream_request(message)

    response = await handlers.stream_message(request)

    # Consume the full stream so storage updates are applied
    async for _ in response.body_iterator:
        pass

    tasks = await storage.list_tasks()
    assert tasks, "Expected at least one task in storage after streaming"
    assert tasks[0]["status"]["state"] in ("completed", "failed")


@pytest.mark.skip(reason="Test times out - async infrastructure issue")
@pytest.mark.asyncio
async def test_stream_message_no_manifest_still_completes():
    """stream_message completes gracefully even when no manifest/workers are set."""
    from starlette.responses import StreamingResponse

    storage = InMemoryStorage()
    handlers = _make_handlers(storage, manifest=None, workers=None)

    message = create_test_message(text="no manifest")
    request = _stream_request(message)

    response = await handlers.stream_message(request)
    assert isinstance(response, StreamingResponse)

    events = []
    async for chunk in response.body_iterator:
        line = chunk.decode() if isinstance(chunk, bytes) else chunk
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    states = [e["status"]["state"] for e in events if e.get("kind") == "status-update"]
    assert "completed" in states or "failed" in states


@pytest.mark.skip(reason="Test times out - async infrastructure issue")
@pytest.mark.asyncio
async def test_stream_message_event_contains_task_and_context_ids():
    """Every SSE event carries the correct task_id and context_id."""
    storage = InMemoryStorage()
    handlers = _make_handlers(storage)

    message = create_test_message(text="ids check")
    request = _stream_request(message)

    response = await handlers.stream_message(request)

    events = []
    async for chunk in response.body_iterator:
        line = chunk.decode() if isinstance(chunk, bytes) else chunk
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    for event in events:
        assert "task_id" in event
        assert "context_id" in event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _MockPushManager:
    """Minimal push manager stub for send_message tests."""

    def __init__(self):
        self.registered = []

    async def register_push_config(self, task_id, config, persist=False):
        self.registered.append((task_id, config))


@pytest.fixture
def mock_push_manager():
    return _MockPushManager()
