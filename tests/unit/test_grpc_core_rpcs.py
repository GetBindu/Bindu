"""Unit tests for core gRPC RPCs."""

from __future__ import annotations

import json
from typing import cast
from uuid import uuid4

import grpc
import pytest

from bindu.grpc import a2a_pb2  # type: ignore[possibly-unbound-import]
from bindu.server.grpc.servicer import A2AServicer
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from tests.mocks import MockAgent, MockManifest
from tests.utils import create_test_message


class DummyContext:
    """Minimal gRPC context stand-in for unit tests."""

    def __init__(self) -> None:
        self.code = None
        self.details = None

    def set_code(self, code: grpc.StatusCode) -> None:
        self.code = code

    def set_details(self, details: str) -> None:
        self.details = details


class NullListStorage(InMemoryStorage):
    """Storage that simulates list_tasks returning None."""

    async def list_tasks(self, length: int | None = None):  # type: ignore[override]
        return None


class ErrorListContextsManager:
    """TaskManager stub that returns JSON-RPC errors for ListContexts."""

    async def list_contexts(self, _request):  # noqa: D401, ANN001
        return {"error": {"code": -32020, "message": "Context not found"}}


def _build_proto_message(text: str = "Test message") -> a2a_pb2.Message:
    message = create_test_message(text=text)
    return a2a_pb2.Message(
        message_id=str(message["message_id"]),
        context_id=str(message["context_id"]),
        task_id=str(message["task_id"]),
        parts=[a2a_pb2.Part(text=a2a_pb2.TextPart(text=text))],
        role="user",
        kind="message",
    )


@pytest.mark.asyncio
async def test_grpc_list_tasks_success():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            for i in range(3):
                message = create_test_message(text=f"Task {i}")
                await storage.submit_task(message["context_id"], message)

            context = DummyContext()
            response = await servicer.ListTasks(
                a2a_pb2.ListTasksRequest(limit=2), context
            )

            assert context.code is None
            assert len(response.tasks) == 2


@pytest.mark.asyncio
async def test_grpc_list_tasks_error():
    storage = NullListStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            context = DummyContext()
            with pytest.raises(RuntimeError):
                await servicer.ListTasks(a2a_pb2.ListTasksRequest(), context)
            assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_cancel_task_success():
    storage = InMemoryStorage()
    manifest = MockManifest()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=manifest
        ) as tm:
            servicer = A2AServicer(tm)

            message = create_test_message(text="Cancel me")
            await storage.submit_task(message["context_id"], message)

            request = a2a_pb2.TaskIdRequest(task_id=str(message["task_id"]))
            context = DummyContext()
            response = await servicer.CancelTask(request, context)

            assert context.code is None
            assert response.id == str(message["task_id"])


@pytest.mark.asyncio
async def test_grpc_cancel_task_error():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)
            request = a2a_pb2.TaskIdRequest(task_id=str(uuid4()))
            context = DummyContext()

            with pytest.raises(RuntimeError):
                await servicer.CancelTask(request, context)
            assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_task_feedback_success():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            message = create_test_message(text="Feedback")
            await storage.submit_task(message["context_id"], message)

            request = a2a_pb2.TaskFeedbackRequest(
                task_id=str(message["task_id"]),
                feedback="Great job!",
                rating=5,
                metadata={"helpful": "true"},
            )
            context = DummyContext()
            response = await servicer.TaskFeedback(request, context)

            assert context.code is None
            assert response.success is True
            assert response.message


@pytest.mark.asyncio
async def test_grpc_task_feedback_error():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            request = a2a_pb2.TaskFeedbackRequest(
                task_id=str(uuid4()),
                feedback="Missing task",
            )
            context = DummyContext()

            with pytest.raises(RuntimeError):
                await servicer.TaskFeedback(request, context)
            assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_list_contexts_success():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            for i in range(2):
                message = create_test_message(text=f"Context {i}")
                await storage.submit_task(message["context_id"], message)

            context = DummyContext()
            response = await servicer.ListContexts(
                a2a_pb2.ListContextsRequest(limit=10), context
            )

            assert context.code is None
            assert len(response.contexts) == 2

            for ctx in response.contexts:
                assert ctx.context_id
                assert len(ctx.messages) == 0
                assert "task_count" in ctx.metadata
                assert "task_ids" in ctx.metadata
                task_ids = json.loads(ctx.metadata["task_ids"])
                assert len(task_ids) == int(ctx.metadata["task_count"])


@pytest.mark.asyncio
async def test_grpc_list_contexts_error():
    servicer = A2AServicer(cast(TaskManager, ErrorListContextsManager()))
    context = DummyContext()
    with pytest.raises(RuntimeError):
        await servicer.ListContexts(a2a_pb2.ListContextsRequest(), context)
    assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_clear_context_success():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            message = create_test_message(text="To clear")
            await storage.submit_task(message["context_id"], message)

            request = a2a_pb2.ContextIdRequest(context_id=str(message["context_id"]))
            context = DummyContext()
            response = await servicer.ClearContext(request, context)

            assert context.code is None
            assert response.success is True


@pytest.mark.asyncio
async def test_grpc_clear_context_error():
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=None
        ) as tm:
            servicer = A2AServicer(tm)

            request = a2a_pb2.ContextIdRequest(context_id=str(uuid4()))
            context = DummyContext()

            with pytest.raises(RuntimeError):
                await servicer.ClearContext(request, context)
            assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_stream_message_success():
    storage = InMemoryStorage()
    manifest = MockManifest()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=manifest
        ) as tm:
            servicer = A2AServicer(tm)

            request = a2a_pb2.MessageSendRequest(message=_build_proto_message())
            context = DummyContext()
            events = [event async for event in servicer.StreamMessage(request, context)]

            status_updates = [
                event.status_update
                for event in events
                if event.HasField("status_update")
            ]
            artifact_updates = [
                event.artifact_update
                for event in events
                if event.HasField("artifact_update")
            ]

            assert status_updates
            assert artifact_updates
            assert any(
                update.final and update.status.state == "completed"
                for update in status_updates
            )


@pytest.mark.asyncio
async def test_grpc_stream_message_error():
    storage = InMemoryStorage()
    manifest = MockManifest(agent_fn=MockAgent(response_type="error"))
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler, storage=storage, manifest=manifest
        ) as tm:
            servicer = A2AServicer(tm)

            request = a2a_pb2.MessageSendRequest(message=_build_proto_message())
            context = DummyContext()
            events = [event async for event in servicer.StreamMessage(request, context)]

            status_updates = [
                event.status_update
                for event in events
                if event.HasField("status_update")
            ]
            failed_updates = [
                update
                for update in status_updates
                if update.final and update.status.state == "failed"
            ]

            assert failed_updates
            assert "error" in failed_updates[0].metadata
