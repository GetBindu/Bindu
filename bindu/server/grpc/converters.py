"""Type conversion utilities between Pydantic models and Protocol Buffers.

This module provides bidirectional conversion between Bindu's Pydantic-based
protocol types and gRPC Protocol Buffer messages.

Note: This module requires generated protobuf code. Run:
    python scripts/generate_proto.py
"""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
from typing import Any, cast
from uuid import UUID

from google.protobuf import json_format, struct_pb2

from bindu.common.protocol.types import (
    Artifact,
    Message,
    Part,
    PushNotificationConfig,
    SecurityScheme,
    Task,
    TaskPushNotificationConfig,
    TaskStatus,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
    FilePart,
    DataPart,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.converters")

# These will be imported after protobuf code is generated
# from bindu.grpc import a2a_pb2

a2a_pb2: Any | None
try:
    a2a_pb2 = importlib.import_module("bindu.grpc.a2a_pb2")
except ImportError:
    a2a_pb2 = None
    logger.warning("Protobuf code not generated. Run: python scripts/generate_proto.py")


def uuid_to_str(uuid_value: UUID | str | None) -> str:
    """Convert UUID to string."""
    if uuid_value is None:
        return ""
    if isinstance(uuid_value, UUID):
        return str(uuid_value)
    return str(uuid_value)


def str_to_uuid(uuid_str: str | None) -> UUID | None:
    """Convert string to UUID."""
    if not uuid_str:
        return None
    try:
        return UUID(uuid_str)
    except (ValueError, AttributeError):
        return None


def _struct_to_dict(value: Any) -> dict[str, Any]:
    """Convert protobuf Struct to a Python dict."""
    return json_format.MessageToDict(value, preserving_proto_field_name=True)


def _dict_to_struct(value: dict[str, Any]) -> Any:
    """Convert Python dict to protobuf Struct."""
    struct = struct_pb2.Struct()  # type: ignore[unresolved-attribute]
    json_format.ParseDict(value, struct)
    return struct


def push_notification_config_to_proto(config: PushNotificationConfig) -> Any:
    """Convert Pydantic PushNotificationConfig to protobuf PushNotificationConfig."""
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_config = a2a_pb2.PushNotificationConfig()
    proto_config.id = uuid_to_str(config.get("id"))
    proto_config.url = config.get("url", "")

    token = config.get("token")
    if token is not None:
        proto_config.token = token

    authentication = config.get("authentication")
    if authentication is not None:
        proto_config.authentication.CopyFrom(_dict_to_struct(dict(authentication)))

    return proto_config


def proto_to_push_notification_config(proto_config: Any) -> PushNotificationConfig:
    """Convert protobuf PushNotificationConfig to Pydantic PushNotificationConfig."""
    config = cast(
        PushNotificationConfig,
        {
            "id": str_to_uuid(proto_config.id) or UUID(int=0),
            "url": proto_config.url,
        },
    )

    if proto_config.token:
        config["token"] = proto_config.token

    if proto_config.HasField("authentication"):
        if proto_config.authentication.fields:
            config["authentication"] = cast(
                SecurityScheme, _struct_to_dict(proto_config.authentication)
            )

    return config


def task_push_notification_config_to_proto(config: TaskPushNotificationConfig) -> Any:
    """Convert Pydantic TaskPushNotificationConfig to protobuf TaskPushNotificationConfig."""
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_config = a2a_pb2.TaskPushNotificationConfig()
    proto_config.id = uuid_to_str(config.get("id"))
    proto_config.push_notification_config.CopyFrom(
        push_notification_config_to_proto(config["push_notification_config"])
    )

    if config.get("long_running") is not None:
        proto_config.long_running = bool(config["long_running"])

    return proto_config


def proto_to_task_push_notification_config(
    proto_config: Any,
) -> TaskPushNotificationConfig:
    """Convert protobuf TaskPushNotificationConfig to Pydantic TaskPushNotificationConfig."""
    config = cast(
        TaskPushNotificationConfig,
        {
            "id": str_to_uuid(proto_config.id) or UUID(int=0),
            "push_notification_config": proto_to_push_notification_config(
                proto_config.push_notification_config
            ),
        },
    )

    if proto_config.long_running:
        config["long_running"] = proto_config.long_running

    return config


def part_to_proto(part: Part) -> Any:
    """Convert Pydantic Part to protobuf Part.

    Args:
        part: Pydantic Part (TextPart, FilePart, or DataPart)

    Returns:
        Protobuf Part message
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_part = a2a_pb2.Part()

    if part["kind"] == "text":
        text_part = a2a_pb2.TextPart()
        text_part.text = part.get("text", "")
        if "metadata" in part:
            text_part.metadata.update(part["metadata"])
        if "embeddings" in part:
            text_part.embeddings.extend(part["embeddings"])
        proto_part.text.CopyFrom(text_part)

    elif part["kind"] == "file":
        file_part = a2a_pb2.FilePart()
        file_info = part.get("file", {})
        file_part.file_id = file_info.get("uri") or file_info.get("bytes", "")
        file_part.mime_type = file_info.get("mimeType", "")
        file_part.filename = file_info.get("name", "")
        if "metadata" in part:
            file_part.metadata.update(part.get("metadata", {}))
        proto_part.file.CopyFrom(file_part)

    elif part["kind"] == "data":
        data_part = a2a_pb2.DataPart()
        data_part.mime_type = part.get("data", {}).get("mimeType", "application/json")

        data_part.data = json.dumps(part.get("data", {})).encode("utf-8")
        if "metadata" in part:
            data_part.metadata.update(part.get("metadata", {}))
        proto_part.data.CopyFrom(data_part)

    return proto_part


def proto_to_part(proto_part: Any) -> Part:
    """Convert protobuf Part to Pydantic Part.

    Args:
        proto_part: Protobuf Part message

    Returns:
        Pydantic Part (TextPart, FilePart, or DataPart)
    """
    if proto_part.HasField("text"):
        text_proto = proto_part.text
        part = cast(
            TextPart,
            {
                "kind": "text",
                "text": text_proto.text,
            },
        )
        if text_proto.metadata:
            part["metadata"] = dict(text_proto.metadata)
        if text_proto.embeddings:
            part["embeddings"] = list(text_proto.embeddings)
        return part

    elif proto_part.HasField("file"):
        file_proto = proto_part.file
        part = cast(
            FilePart,
            {
                "kind": "file",
                "text": "",  # FilePart extends TextPart
                "file": {
                    "uri": file_proto.file_id,
                    "mimeType": file_proto.mime_type,
                    "name": file_proto.filename,
                    "bytes": "",
                },
            },
        )
        if file_proto.metadata:
            part["metadata"] = dict(file_proto.metadata)
        return part

    elif proto_part.HasField("data"):
        data_proto = proto_part.data

        part = cast(
            DataPart,
            {
                "kind": "data",
                "text": "",  # DataPart extends TextPart
                "data": json.loads(data_proto.data.decode("utf-8")),
            },
        )
        if data_proto.metadata:
            part["metadata"] = dict(data_proto.metadata)
        return part

    raise ValueError(f"Unknown part type: {proto_part}")


def message_to_proto(msg: Message) -> Any:
    """Convert Pydantic Message to protobuf Message.

    Args:
        msg: Pydantic Message

    Returns:
        Protobuf Message
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_msg = a2a_pb2.Message()
    proto_msg.message_id = uuid_to_str(msg.get("message_id"))
    proto_msg.context_id = uuid_to_str(msg.get("context_id"))
    proto_msg.task_id = uuid_to_str(msg.get("task_id"))

    if "reference_task_ids" in msg:
        proto_msg.reference_task_ids.extend(
            [uuid_to_str(ref_id) for ref_id in msg["reference_task_ids"]]
        )

    proto_msg.kind = msg.get("kind", "message")
    proto_msg.role = msg.get("role", "user")

    if "metadata" in msg and msg["metadata"]:
        proto_msg.metadata.update({str(k): str(v) for k, v in msg["metadata"].items()})

    if "parts" in msg:
        for part in msg["parts"]:
            proto_part = part_to_proto(part)
            proto_msg.parts.append(proto_part)

    if "extensions" in msg:
        proto_msg.extensions.extend(msg["extensions"])

    return proto_msg


def proto_to_message(proto_msg: Any) -> Message:
    """Convert protobuf Message to Pydantic Message.

    Args:
        proto_msg: Protobuf Message

    Returns:
        Pydantic Message
    """
    msg = cast(
        Message,
        {
            "message_id": str_to_uuid(proto_msg.message_id) or UUID(int=0),
            "context_id": str_to_uuid(proto_msg.context_id) or UUID(int=0),
            "task_id": str_to_uuid(proto_msg.task_id) or UUID(int=0),
            "kind": "message",
            "parts": [proto_to_part(part) for part in proto_msg.parts],
            "role": proto_msg.role or "user",
        },
    )

    if proto_msg.reference_task_ids:
        reference_task_ids: list[UUID] = []
        for ref_id in proto_msg.reference_task_ids:
            if not ref_id:
                continue
            parsed_id = str_to_uuid(ref_id)
            if parsed_id:
                reference_task_ids.append(parsed_id)
        if reference_task_ids:
            msg["reference_task_ids"] = reference_task_ids

    if proto_msg.metadata:
        msg["metadata"] = dict(proto_msg.metadata)

    if proto_msg.extensions:
        msg["extensions"] = list(proto_msg.extensions)

    return msg


def task_status_to_proto(status: TaskStatus) -> Any:
    """Convert Pydantic TaskStatus to protobuf TaskStatus.

    Args:
        status: Pydantic TaskStatus

    Returns:
        Protobuf TaskStatus
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_status = a2a_pb2.TaskStatus()
    proto_status.state = status.get("state", "unknown")
    proto_status.timestamp = status.get(
        "timestamp", datetime.now(timezone.utc).isoformat()
    )

    if "message" in status and status["message"]:
        proto_status.message.CopyFrom(message_to_proto(status["message"]))

    return proto_status


def proto_to_task_status(proto_status: Any) -> TaskStatus:
    """Convert protobuf TaskStatus to Pydantic TaskStatus.

    Args:
        proto_status: Protobuf TaskStatus

    Returns:
        Pydantic TaskStatus
    """
    status = cast(
        TaskStatus,
        {
            "state": proto_status.state or "unknown",
            "timestamp": proto_status.timestamp
            or datetime.now(timezone.utc).isoformat(),
        },
    )

    if proto_status.HasField("message"):
        status["message"] = proto_to_message(proto_status.message)

    return status


def task_to_proto(task: Task) -> Any:
    """Convert Pydantic Task to protobuf Task.

    Args:
        task: Pydantic Task

    Returns:
        Protobuf Task
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_task = a2a_pb2.Task()
    proto_task.id = uuid_to_str(task.get("id"))
    proto_task.context_id = uuid_to_str(task.get("context_id"))
    proto_task.kind = task.get("kind", "task")

    if "status" in task:
        proto_task.status.CopyFrom(task_status_to_proto(task["status"]))

    if "artifacts" in task:
        for artifact in task["artifacts"]:
            proto_artifact = artifact_to_proto(artifact)
            proto_task.artifacts.append(proto_artifact)

    if "history" in task:
        for msg in task["history"]:
            proto_msg = message_to_proto(msg)
            proto_task.history.append(proto_msg)

    if "metadata" in task and task["metadata"]:
        proto_task.metadata.update(
            {str(k): str(v) for k, v in task["metadata"].items()}
        )

    return proto_task


def proto_to_task(proto_task: Any) -> Task:
    """Convert protobuf Task to Pydantic Task.

    Args:
        proto_task: Protobuf Task

    Returns:
        Pydantic Task
    """
    task = cast(
        Task,
        {
            "id": str_to_uuid(proto_task.id) or UUID(int=0),
            "context_id": str_to_uuid(proto_task.context_id) or UUID(int=0),
            "kind": proto_task.kind or "task",
            "status": proto_to_task_status(proto_task.status),
            "artifacts": [
                proto_to_artifact(artifact) for artifact in proto_task.artifacts
            ],
            "history": [proto_to_message(msg) for msg in proto_task.history],
        },
    )

    if proto_task.metadata:
        task["metadata"] = dict(proto_task.metadata)

    return task


def artifact_to_proto(artifact: Artifact) -> Any:
    """Convert Pydantic Artifact to protobuf Artifact.

    Args:
        artifact: Pydantic Artifact

    Returns:
        Protobuf Artifact
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_artifact = a2a_pb2.Artifact()
    proto_artifact.artifact_id = uuid_to_str(artifact.get("artifact_id"))
    proto_artifact.name = artifact.get("name", "")

    if "parts" in artifact:
        for part in artifact["parts"]:
            proto_part = part_to_proto(part)
            proto_artifact.parts.append(proto_part)

    if "metadata" in artifact and artifact["metadata"]:
        proto_artifact.metadata.update(
            {str(k): str(v) for k, v in artifact["metadata"].items()}
        )

    return proto_artifact


def proto_to_artifact(proto_artifact: Any) -> Artifact:
    """Convert protobuf Artifact to Pydantic Artifact.

    Args:
        proto_artifact: Protobuf Artifact

    Returns:
        Pydantic Artifact
    """
    artifact = cast(
        Artifact,
        {
            "artifact_id": str_to_uuid(proto_artifact.artifact_id) or UUID(int=0),
            "name": proto_artifact.name or "",
            "parts": [proto_to_part(part) for part in proto_artifact.parts],
        },
    )

    if proto_artifact.metadata:
        artifact["metadata"] = dict(proto_artifact.metadata)

    if proto_artifact.name:
        artifact["name"] = proto_artifact.name

    return artifact


def context_summary_to_proto(context_summary: dict[str, Any]) -> Any:
    """Convert context summary dict to protobuf Context.

    Uses metadata mapping for task_count and task_ids as documented in
    GRPC_CONTEXT_CONVERTER_DECISION.md.
    """
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_context = a2a_pb2.Context()
    proto_context.context_id = uuid_to_str(context_summary.get("context_id"))

    metadata: dict[str, str] = {}
    task_count = context_summary.get("task_count")
    if task_count is not None:
        metadata["task_count"] = str(task_count)

    task_ids = context_summary.get("task_ids") or []
    metadata["task_ids"] = json.dumps([uuid_to_str(task_id) for task_id in task_ids])

    if metadata:
        proto_context.metadata.update(metadata)

    return proto_context


def task_status_update_event_to_proto(event: TaskStatusUpdateEvent) -> Any:
    """Convert TaskStatusUpdateEvent dict to protobuf TaskStatusUpdateEvent."""
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_event = a2a_pb2.TaskStatusUpdateEvent()
    proto_event.task_id = uuid_to_str(event.get("task_id"))
    proto_event.context_id = uuid_to_str(event.get("context_id"))
    proto_event.final = bool(event.get("final", False))
    proto_event.status.CopyFrom(task_status_to_proto(event["status"]))

    metadata = event.get("metadata")
    if metadata:
        proto_event.metadata.update({str(k): str(v) for k, v in metadata.items()})

    return proto_event


def task_artifact_update_event_to_proto(event: TaskArtifactUpdateEvent) -> Any:
    """Convert TaskArtifactUpdateEvent dict to protobuf TaskArtifactUpdateEvent."""
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    proto_event = a2a_pb2.TaskArtifactUpdateEvent()
    proto_event.task_id = uuid_to_str(event.get("task_id"))
    proto_event.context_id = uuid_to_str(event.get("context_id"))
    proto_event.append = bool(event.get("append", False))
    proto_event.last_chunk = bool(event.get("last_chunk", False))
    proto_event.artifact.CopyFrom(artifact_to_proto(event["artifact"]))

    metadata = event.get("metadata")
    if metadata:
        proto_event.metadata.update({str(k): str(v) for k, v in metadata.items()})

    return proto_event


def task_event_to_proto(event: dict[str, Any]) -> Any:
    """Convert a status/artifact event dict to protobuf TaskEvent."""
    if a2a_pb2 is None:
        raise ImportError(
            "Protobuf code not generated. Run: python scripts/generate_proto.py"
        )

    kind = event.get("kind")
    proto_event = a2a_pb2.TaskEvent()

    if kind == "status-update":
        status_event = dict(event)
        if "error" in status_event:
            metadata = dict(status_event.get("metadata") or {})
            metadata["error"] = str(status_event["error"])
            status_event["metadata"] = metadata
        proto_event.status_update.CopyFrom(
            task_status_update_event_to_proto(status_event)  # type: ignore[arg-type]
        )
        return proto_event

    if kind == "artifact-update":
        proto_event.artifact_update.CopyFrom(
            task_artifact_update_event_to_proto(event)  # type: ignore[arg-type]
        )
        return proto_event

    raise ValueError(f"Unknown task event kind: {kind}")
