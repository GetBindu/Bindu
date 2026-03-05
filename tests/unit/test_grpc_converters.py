"""Unit tests for gRPC converter utilities."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest

from bindu.grpc import a2a_pb2  # type: ignore[possibly-unbound-import]
from bindu.server.grpc.converters import (
    context_summary_to_proto,
    part_to_proto,
    proto_to_part,
    proto_to_task_push_notification_config,
    push_notification_config_to_proto,
    proto_to_push_notification_config,
    task_event_to_proto,
    task_push_notification_config_to_proto,
)
from bindu.common.protocol.types import (
    PushNotificationConfig,
    TaskPushNotificationConfig,
)


def test_part_text_roundtrip() -> None:
    part = {"kind": "text", "text": "hello", "metadata": {"lang": "en"}}

    proto_part = part_to_proto(part)
    converted = proto_to_part(proto_part)

    assert converted["kind"] == "text"
    assert converted["text"] == "hello"
    assert converted["metadata"]["lang"] == "en"


def test_part_file_roundtrip() -> None:
    part = {
        "kind": "file",
        "text": "",
        "file": {"uri": "file://abc", "mimeType": "text/plain", "name": "a.txt"},
    }

    proto_part = part_to_proto(part)
    converted = proto_to_part(proto_part)

    assert converted["kind"] == "file"
    assert converted["file"]["uri"] == "file://abc"
    assert converted["file"]["mimeType"] == "text/plain"


def test_part_data_roundtrip() -> None:
    part = {
        "kind": "data",
        "text": "",
        "data": {"mimeType": "application/json", "value": {"a": 1}},
        "metadata": {"source": "test"},
    }

    proto_part = part_to_proto(part)
    converted = proto_to_part(proto_part)

    assert converted["kind"] == "data"
    assert converted["data"]["value"]["a"] == 1
    assert converted["metadata"]["source"] == "test"


def test_proto_to_part_unknown_raises() -> None:
    empty_part = a2a_pb2.Part()

    with pytest.raises(ValueError):
        proto_to_part(empty_part)


def test_context_summary_to_proto_serializes_task_metadata() -> None:
    context_id = uuid4()
    task_ids = [uuid4(), uuid4()]

    proto_context = context_summary_to_proto(
        {"context_id": context_id, "task_count": 2, "task_ids": task_ids}
    )

    assert proto_context.context_id == str(context_id)
    assert proto_context.metadata["task_count"] == "2"
    parsed_ids = json.loads(proto_context.metadata["task_ids"])
    assert parsed_ids == [str(task_ids[0]), str(task_ids[1])]


def test_push_notification_config_roundtrip() -> None:
    from typing import cast

    config = cast(
        PushNotificationConfig,
        {
            "id": uuid4(),
            "url": "https://example.com/hook",
            "token": "secret",
            "authentication": {
                "type": "http",
                "scheme": "bearer",
                "description": "some token",
            },
        },
    )

    proto_config = push_notification_config_to_proto(config)
    converted = proto_to_push_notification_config(proto_config)

    assert converted["url"] == "https://example.com/hook"
    assert converted["token"] == "secret"
    assert converted["authentication"]["type"] == "http"
    assert converted["authentication"]["scheme"] == "bearer"


def test_task_push_notification_config_long_running_false_not_set() -> None:
    from typing import cast

    config = cast(
        TaskPushNotificationConfig,
        {
            "id": uuid4(),
            "push_notification_config": {
                "id": uuid4(),
                "url": "https://example.com/hook",
            },
            "long_running": False,
        },
    )

    proto_config = task_push_notification_config_to_proto(config)
    converted = proto_to_task_push_notification_config(proto_config)

    assert converted["push_notification_config"]["url"] == "https://example.com/hook"
    assert "long_running" not in converted


def test_task_event_status_update_includes_error_metadata() -> None:
    event = {
        "kind": "status-update",
        "task_id": uuid4(),
        "context_id": uuid4(),
        "final": True,
        "status": {
            "state": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": "boom",
    }

    proto_event = task_event_to_proto(event)

    assert proto_event.HasField("status_update")
    assert proto_event.status_update.metadata["error"] == "boom"


def test_task_event_artifact_update() -> None:
    event = {
        "kind": "artifact-update",
        "task_id": uuid4(),
        "context_id": uuid4(),
        "append": False,
        "last_chunk": True,
        "artifact": {
            "artifact_id": uuid4(),
            "name": "result",
            "parts": [{"kind": "text", "text": "ok"}],
        },
    }

    proto_event = task_event_to_proto(event)

    assert proto_event.HasField("artifact_update")
    assert proto_event.artifact_update.last_chunk is True


def test_task_event_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        task_event_to_proto({"kind": "unknown"})


def test_message_roundtrip() -> None:
    from bindu.server.grpc.converters import message_to_proto, proto_to_message
    from uuid import uuid4
    from typing import cast
    from bindu.common.protocol.types import Message

    msg = cast(
        Message,
        {
            "message_id": uuid4(),
            "context_id": uuid4(),
            "task_id": uuid4(),
            "reference_task_ids": [uuid4()],
            "kind": "message",
            "role": "agent",
            "metadata": {"foo": "bar"},
            "parts": [{"kind": "text", "text": "test"}],
            "extensions": ["x402"],
        },
    )
    proto_msg = message_to_proto(msg)
    converted = proto_to_message(proto_msg)
    assert converted["role"] == "agent"
    assert converted["metadata"]["foo"] == "bar"
    assert converted["parts"][0]["text"] == "test"
    assert converted["extensions"][0] == "x402"


def test_task_status_roundtrip() -> None:
    from typing import cast
    from bindu.common.protocol.types import TaskStatus
    from bindu.server.grpc.converters import task_status_to_proto, proto_to_task_status

    status = cast(
        TaskStatus, {"state": "completed", "timestamp": "2023-10-27T10:00:00Z"}
    )
    proto = task_status_to_proto(status)
    converted = proto_to_task_status(proto)
    assert converted["state"] == "completed"


def test_artifact_roundtrip() -> None:
    from bindu.server.grpc.converters import artifact_to_proto, proto_to_artifact
    from bindu.common.protocol.types import Artifact
    from uuid import uuid4
    from typing import cast

    art = cast(
        Artifact,
        {
            "artifact_id": uuid4(),
            "name": "art",
            "metadata": {"x": "y"},
            "parts": [{"kind": "text", "text": "t"}],
        },
    )
    proto = artifact_to_proto(art)
    converted = proto_to_artifact(proto)
    assert converted["name"] == "art"
    assert converted["metadata"]["x"] == "y"


def test_task_roundtrip() -> None:
    from bindu.server.grpc.converters import task_to_proto, proto_to_task
    from bindu.common.protocol.types import Task
    from uuid import uuid4
    from typing import cast

    task = cast(
        Task,
        {
            "id": uuid4(),
            "context_id": uuid4(),
            "kind": "task",
            "status": {"state": "working", "timestamp": "2023"},
            "artifacts": [{"artifact_id": uuid4(), "name": "art", "parts": []}],
            "history": [],
            "metadata": {"test": "val"},
        },
    )
    proto = task_to_proto(task)
    converted = proto_to_task(proto)
    assert converted["kind"] == "task"
    assert converted["status"]["state"] == "working"
    assert converted["metadata"]["test"] == "val"
