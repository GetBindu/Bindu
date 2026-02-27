"""Unit tests for message/stream lifecycle and endpoint handling."""

import asyncio
import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from starlette.requests import Request
from starlette.responses import StreamingResponse

from bindu.common.protocol.types import StreamMessageRequest
from bindu.server.applications import BinduApplication
from bindu.server.endpoints.a2a_protocol import agent_run_endpoint
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from tests.mocks import MockManifest
from tests.utils import create_test_message


def _make_request(payload: dict[str, Any]) -> Request:
    """Create a Starlette request with a JSON body."""
    body = json.dumps(payload).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope, receive)


async def _read_sse_events(response: StreamingResponse) -> list[dict[str, Any]]:
    """Read all SSE events from a streaming response."""
    events: list[dict[str, Any]] = []

    async for chunk in response.body_iterator:
        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        for line in text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    return events


@pytest.mark.asyncio
async def test_agent_endpoint_returns_stream_response_directly():
    """A2A endpoint should pass through StreamingResponse for message/stream."""

    async def stream_handler(_request):
        async def generator():
            event = {"kind": "status-update", "status": {"state": "working"}}
            yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")

    app = SimpleNamespace(task_manager=SimpleNamespace(stream_message=stream_handler))
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/stream",
        "params": {
            "message": {
                "messageId": str(uuid4()),
                "contextId": str(uuid4()),
                "taskId": str(uuid4()),
                "kind": "message",
                "parts": [{"kind": "text", "text": "hello"}],
                "role": "user",
            }
        },
    }

    response = await agent_run_endpoint(cast(BinduApplication, app), _make_request(payload))

    assert isinstance(response, StreamingResponse)
    events = await asyncio.wait_for(_read_sse_events(response), timeout=2)
    assert events
    assert events[0]["kind"] == "status-update"


@pytest.mark.asyncio
async def test_stream_message_follows_task_lifecycle():
    """message/stream should schedule work and emit lifecycle updates."""
    storage = InMemoryStorage()
    manifest = MockManifest()

    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=manifest
        ) as task_manager:
            message = create_test_message(text="stream this")
            request = cast(
                StreamMessageRequest,
                {
                    "jsonrpc": "2.0",
                    "id": uuid4(),
                    "method": "message/stream",
                    "params": {"message": message},
                },
            )

            response = await task_manager.stream_message(request)

            assert isinstance(response, StreamingResponse)
            events = await asyncio.wait_for(_read_sse_events(response), timeout=3)
            status_events = [e for e in events if e.get("kind") == "status-update"]
            artifact_events = [e for e in events if e.get("kind") == "artifact-update"]

            assert status_events
            states = [e["status"]["state"] for e in status_events]
            assert states[0] == "submitted"
            assert "working" in states[1:]
            assert "completed" in states[1:]
            assert states.index("working") < states.index("completed")

            assert artifact_events
            assert all(
                e.get("artifact", {}).get("artifact_id") is not None
                for e in artifact_events
            )

            task = await storage.load_task(message["task_id"])
            assert task is not None
            assert task["status"]["state"] == "completed"
