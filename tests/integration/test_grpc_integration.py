"""gRPC integration tests using a real server and in-process JSON-RPC parity."""

from __future__ import annotations

from contextlib import asynccontextmanager
import importlib
import sys
from typing import AsyncGenerator, cast
from uuid import UUID

import grpc
from grpc import aio  # type: ignore[possibly-unbound-import]
import httpx
import pytest

from bindu.common.models import AgentManifest
from bindu.grpc import a2a_pb2  # type: ignore[possibly-unbound-import]
from bindu.server.applications import BinduApplication
from bindu.server.grpc.auth import HydraTokenValidator
from bindu.server.grpc.server import GrpcServer
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from bindu.settings import app_settings
from tests.mocks import MockAgent, MockManifest
from tests.utils import get_deterministic_uuid

sys.modules.setdefault("a2a_pb2", a2a_pb2)
a2a_pb2_grpc = importlib.import_module("bindu.grpc.a2a_pb2_grpc")

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class _NoopSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401, ANN001
        return False

    def set_attributes(self, *_args, **_kwargs):  # noqa: D401
        return None

    def set_attribute(self, *_args, **_kwargs):  # noqa: D401
        return None

    def set_status(self, *_args, **_kwargs):  # noqa: D401
        return None

    def add_event(self, *_args, **_kwargs):  # noqa: D401
        return None


def _patch_worker_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    import bindu.server.workers.base as worker_base

    def _start_as_current_span(*_args, **_kwargs):
        return _NoopSpan()

    monkeypatch.setattr(
        worker_base.tracer, "start_as_current_span", _start_as_current_span
    )


def _build_app(agent: MockAgent | None = None) -> BinduApplication:
    storage = InMemoryStorage()
    scheduler = InMemoryScheduler()
    manifest = MockManifest(agent_fn=agent or MockAgent())

    @asynccontextmanager
    async def test_lifespan(app: BinduApplication) -> AsyncGenerator[None, None]:
        app._storage = storage
        app._scheduler = scheduler
        task_manager = TaskManager(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )
        async with task_manager:
            app.task_manager = task_manager
            yield

    return BinduApplication(
        manifest=cast(AgentManifest, manifest),
        url="http://localhost:3773",
        version="1.0.0",
        lifespan=test_lifespan,
    )


@asynccontextmanager
async def _run_app(
    agent: MockAgent | None = None,
) -> AsyncGenerator[BinduApplication, None]:
    app = _build_app(agent)
    async with app.router.lifespan_context(app):
        yield app


@asynccontextmanager
async def _run_grpc_server(
    app: BinduApplication, port: int
) -> AsyncGenerator[str, None]:
    grpc_server = GrpcServer(app, port=port, host="127.0.0.1")
    await grpc_server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await grpc_server.stop()


def _build_proto_message(
    *,
    text: str,
    message_id: UUID,
    context_id: UUID,
    task_id: UUID,
) -> a2a_pb2.Message:
    return a2a_pb2.Message(
        message_id=str(message_id),
        context_id=str(context_id),
        task_id=str(task_id),
        parts=[a2a_pb2.Part(text=a2a_pb2.TextPart(text=text))],
        role="user",
        kind="message",
    )


def _build_jsonrpc_payload(
    *,
    text: str,
    message_id: UUID,
    context_id: UUID,
    task_id: UUID,
) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "kind": "message",
                "messageId": str(message_id),
                "contextId": str(context_id),
                "taskId": str(task_id),
            },
            "configuration": {"acceptedOutputModes": ["application/json"]},
        },
        "id": str(get_deterministic_uuid(90)),
    }


def _extract_task_id(task: dict) -> str:
    for key in ("id", "taskId", "task_id"):
        value = task.get(key)
        if value:
            return str(value)
    raise AssertionError("JSON-RPC task id not found")


def _extract_context_id(task: dict) -> str:
    for key in ("contextId", "context_id"):
        value = task.get(key)
        if value:
            return str(value)
    raise AssertionError("JSON-RPC context id not found")


async def test_send_message_jsonrpc_grpc_parity(
    monkeypatch: pytest.MonkeyPatch, unused_tcp_port: int
) -> None:
    _patch_worker_tracer(monkeypatch)
    message_id = get_deterministic_uuid(1)
    context_id = get_deterministic_uuid(2)
    task_id = get_deterministic_uuid(3)
    agent = MockAgent(response="Need more input", response_type="input-required")

    async with _run_app(agent) as app:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            payload = _build_jsonrpc_payload(
                text="Hello from parity test",
                message_id=message_id,
                context_id=context_id,
                task_id=task_id,
            )
            jsonrpc_response = await client.post("/", json=payload)

            assert jsonrpc_response.status_code == 200
            json_data = jsonrpc_response.json()
            assert "result" in json_data
            json_task = json_data["result"]

        async with _run_grpc_server(app, unused_tcp_port) as target:
            channel = aio.insecure_channel(target)
            await channel.channel_ready()
            stub = a2a_pb2_grpc.A2AServiceStub(channel)
            grpc_request = a2a_pb2.MessageSendRequest(
                message=_build_proto_message(
                    text="Hello from parity test",
                    message_id=message_id,
                    context_id=context_id,
                    task_id=task_id,
                )
            )
            grpc_response = await stub.SendMessage(grpc_request)
            await channel.close()

    grpc_task = grpc_response.task
    assert _extract_task_id(json_task) == grpc_task.id
    assert _extract_context_id(json_task) == grpc_task.context_id
    assert json_task.get("kind") == grpc_task.kind == "task"
    assert json_task["status"]["state"] in app_settings.agent.non_terminal_states
    assert grpc_task.status.state in app_settings.agent.non_terminal_states


async def test_grpc_stream_message_emits_updates(unused_tcp_port: int) -> None:
    message_id = get_deterministic_uuid(4)
    context_id = get_deterministic_uuid(5)
    task_id = get_deterministic_uuid(6)

    async with _run_app(MockAgent(response="Streaming response")) as app:
        async with _run_grpc_server(app, unused_tcp_port) as target:
            channel = aio.insecure_channel(target)
            await channel.channel_ready()
            stub = a2a_pb2_grpc.A2AServiceStub(channel)
            grpc_request = a2a_pb2.MessageSendRequest(
                message=_build_proto_message(
                    text="Stream this message",
                    message_id=message_id,
                    context_id=context_id,
                    task_id=task_id,
                )
            )
            events = [event async for event in stub.StreamMessage(grpc_request)]
            await channel.close()

    status_updates = [
        event.status_update for event in events if event.HasField("status_update")
    ]
    artifact_updates = [
        event.artifact_update for event in events if event.HasField("artifact_update")
    ]

    assert status_updates
    assert artifact_updates
    assert any(
        update.final and update.status.state == "completed" for update in status_updates
    )


async def test_grpc_auth_metadata_enforced(
    monkeypatch: pytest.MonkeyPatch, unused_tcp_port: int
) -> None:
    monkeypatch.setattr(app_settings.auth, "enabled", True)

    def _validate_ok(self, _token):  # noqa: ARG001
        return {"sub": "test-user"}

    monkeypatch.setattr(HydraTokenValidator, "validate_token", _validate_ok)

    message_id = get_deterministic_uuid(7)
    context_id = get_deterministic_uuid(8)
    task_id = get_deterministic_uuid(9)

    async with _run_app(MockAgent(response="Auth response")) as app:
        async with _run_grpc_server(app, unused_tcp_port) as target:
            channel = aio.insecure_channel(target)
            await channel.channel_ready()
            stub = a2a_pb2_grpc.A2AServiceStub(channel)
            grpc_request = a2a_pb2.MessageSendRequest(
                message=_build_proto_message(
                    text="Auth protected message",
                    message_id=message_id,
                    context_id=context_id,
                    task_id=task_id,
                )
            )

            with pytest.raises(aio.AioRpcError) as exc_info:
                await stub.SendMessage(grpc_request)

            assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
            assert exc_info.value.details() == "Missing authorization token"

            grpc_response = await stub.SendMessage(
                grpc_request,
                metadata=(("authorization", "Bearer test-token"),),
            )
            await channel.close()

    assert grpc_response.task.id == str(task_id)
