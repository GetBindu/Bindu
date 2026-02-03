"""Unit tests for gRPC push notification RPCs."""

from __future__ import annotations

from uuid import uuid4

import grpc
import pytest
from google.protobuf import struct_pb2

from bindu.grpc import a2a_pb2  # type: ignore[possibly-unbound-import]
from bindu.server.grpc.servicer import A2AServicer
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from tests.mocks import MockManifest
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


@pytest.mark.asyncio
async def test_grpc_push_notification_success(task_manager_with_push):
    """Test set/get/list/delete push notification flow."""
    servicer = A2AServicer(task_manager_with_push)

    message = create_test_message()
    await task_manager_with_push.storage.submit_task(message["context_id"], message)

    auth_struct = getattr(struct_pb2, "Struct")()
    auth_struct.update(
        {
            "type": "apiKey",
            "name": "X-API-Key",
            "in": "header",
        }
    )

    push_config_id = uuid4()
    set_request = a2a_pb2.SetTaskPushNotificationRequest(
        config=a2a_pb2.TaskPushNotificationConfig(
            id=str(message["task_id"]),
            push_notification_config=a2a_pb2.PushNotificationConfig(
                id=str(push_config_id),
                url="https://example.com/webhook",
                token="token",
                authentication=auth_struct,
            ),
            long_running=True,
        )
    )

    context = DummyContext()
    set_response = await servicer.SetTaskPushNotification(set_request, context)
    assert context.code is None
    assert set_response.id == str(message["task_id"])
    assert set_response.push_notification_config.url == "https://example.com/webhook"

    get_request = a2a_pb2.GetTaskPushNotificationRequest(
        task_id=str(message["task_id"])
    )
    get_context = DummyContext()
    get_response = await servicer.GetTaskPushNotification(get_request, get_context)
    assert get_context.code is None
    assert get_response.id == str(message["task_id"])
    assert get_response.push_notification_config.id == str(push_config_id)

    list_request = a2a_pb2.ListTaskPushNotificationsRequest(id=str(message["task_id"]))
    list_context = DummyContext()
    list_response = await servicer.ListTaskPushNotifications(list_request, list_context)
    assert list_context.code is None
    assert len(list_response.configs) == 1
    assert list_response.configs[0].id == str(message["task_id"])

    delete_request = a2a_pb2.DeleteTaskPushNotificationRequest(
        id=str(message["task_id"]),
        push_notification_config_id=str(push_config_id),
    )
    delete_context = DummyContext()
    delete_response = await servicer.DeleteTaskPushNotification(
        delete_request, delete_context
    )
    assert delete_context.code is None
    assert delete_response.config.id == str(message["task_id"])


@pytest.mark.asyncio
async def test_grpc_push_notification_not_supported():
    """Test push notification when server does not support push."""
    storage = InMemoryStorage()
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler,
            storage=storage,
            manifest=None,
        ) as tm:
            servicer = A2AServicer(tm)
            task_id = uuid4()

            set_request = a2a_pb2.SetTaskPushNotificationRequest(
                config=a2a_pb2.TaskPushNotificationConfig(
                    id=str(task_id),
                    push_notification_config=a2a_pb2.PushNotificationConfig(
                        id=str(uuid4()),
                        url="https://example.com/webhook",
                    ),
                )
            )

            context = DummyContext()
            with pytest.raises(RuntimeError):
                await servicer.SetTaskPushNotification(set_request, context)
            assert context.code == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_grpc_push_notification_task_not_found():
    """Test setting push notification for a missing task."""
    storage = InMemoryStorage()
    manifest = MockManifest(capabilities={"push_notifications": True})
    async with InMemoryScheduler() as scheduler:
        async with TaskManager(
            scheduler=scheduler,
            storage=storage,
            manifest=manifest,
        ) as tm:
            servicer = A2AServicer(tm)
            task_id = uuid4()

            set_request = a2a_pb2.SetTaskPushNotificationRequest(
                config=a2a_pb2.TaskPushNotificationConfig(
                    id=str(task_id),
                    push_notification_config=a2a_pb2.PushNotificationConfig(
                        id=str(uuid4()),
                        url="https://example.com/webhook",
                    ),
                )
            )

            context = DummyContext()
            with pytest.raises(RuntimeError):
                await servicer.SetTaskPushNotification(set_request, context)
            assert context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_grpc_push_notification_config_mismatch(task_manager_with_push):
    """Test delete push notification config mismatch."""
    servicer = A2AServicer(task_manager_with_push)

    message = create_test_message()
    await task_manager_with_push.storage.submit_task(message["context_id"], message)

    push_config_id = uuid4()
    set_request = a2a_pb2.SetTaskPushNotificationRequest(
        config=a2a_pb2.TaskPushNotificationConfig(
            id=str(message["task_id"]),
            push_notification_config=a2a_pb2.PushNotificationConfig(
                id=str(push_config_id),
                url="https://example.com/webhook",
            ),
        )
    )
    await servicer.SetTaskPushNotification(set_request, DummyContext())

    delete_request = a2a_pb2.DeleteTaskPushNotificationRequest(
        id=str(message["task_id"]),
        push_notification_config_id=str(uuid4()),
    )
    context = DummyContext()
    with pytest.raises(RuntimeError):
        await servicer.DeleteTaskPushNotification(delete_request, context)
    assert context.code == grpc.StatusCode.FAILED_PRECONDITION
