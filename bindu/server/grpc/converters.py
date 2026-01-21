"""Type conversion utilities between Pydantic models and Protocol Buffers.

This module provides bidirectional conversion between Bindu's Pydantic-based
protocol types and gRPC Protocol Buffer messages.

Note: This module requires generated protobuf code. Run:
    python scripts/generate_proto.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from bindu.common.protocol.types import (
    Artifact,
    Message,
    Part,
    Task,
    TaskStatus,
    TextPart,
    FilePart,
    DataPart,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.converters")

# These will be imported after protobuf code is generated
# from bindu.grpc import a2a_pb2

try:
    from bindu.grpc import a2a_pb2
except ImportError:
    a2a_pb2 = None
    logger.warning(
        "Protobuf code not generated. Run: python scripts/generate_proto.py"
    )


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


def part_to_proto(part: Part) -> Any:
    """Convert Pydantic Part to protobuf Part.

    Args:
        part: Pydantic Part (TextPart, FilePart, or DataPart)

    Returns:
        Protobuf Part message
    """
    if a2a_pb2 is None:
        raise ImportError("Protobuf code not generated. Run: python scripts/generate_proto.py")

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
        # Convert dict to JSON bytes
        import json
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
        part: TextPart = {
            "kind": "text",
            "text": text_proto.text,
        }
        if text_proto.metadata:
            part["metadata"] = dict(text_proto.metadata)
        if text_proto.embeddings:
            part["embeddings"] = list(text_proto.embeddings)
        return part

    elif proto_part.HasField("file"):
        file_proto = proto_part.file
        part: FilePart = {
            "kind": "file",
            "text": "",  # FilePart extends TextPart
            "file": {
                "uri": file_proto.file_id,
                "mimeType": file_proto.mime_type,
                "name": file_proto.filename,
            },
        }
        if file_proto.metadata:
            part["metadata"] = dict(file_proto.metadata)
        return part

    elif proto_part.HasField("data"):
        data_proto = proto_part.data
        import json
        part: DataPart = {
            "kind": "data",
            "text": "",  # DataPart extends TextPart
            "data": json.loads(data_proto.data.decode("utf-8")),
        }
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
        raise ImportError("Protobuf code not generated. Run: python scripts/generate_proto.py")

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
    msg: Message = {
        "message_id": str_to_uuid(proto_msg.message_id) or UUID(int=0),
        "context_id": str_to_uuid(proto_msg.context_id) or UUID(int=0),
        "task_id": str_to_uuid(proto_msg.task_id) or UUID(int=0),
        "kind": "message",
        "parts": [proto_to_part(part) for part in proto_msg.parts],
        "role": proto_msg.role or "user",
    }

    if proto_msg.reference_task_ids:
        msg["reference_task_ids"] = [
            str_to_uuid(ref_id) for ref_id in proto_msg.reference_task_ids if ref_id
        ]

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
        raise ImportError("Protobuf code not generated. Run: python scripts/generate_proto.py")

    proto_status = a2a_pb2.TaskStatus()
    proto_status.state = status.get("state", "unknown")
    proto_status.timestamp = status.get("timestamp", datetime.now(timezone.utc).isoformat())

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
    status: TaskStatus = {
        "state": proto_status.state or "unknown",
        "timestamp": proto_status.timestamp or datetime.now(timezone.utc).isoformat(),
    }

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
        raise ImportError("Protobuf code not generated. Run: python scripts/generate_proto.py")

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
        proto_task.metadata.update({str(k): str(v) for k, v in task["metadata"].items()})

    return proto_task


def proto_to_task(proto_task: Any) -> Task:
    """Convert protobuf Task to Pydantic Task.

    Args:
        proto_task: Protobuf Task

    Returns:
        Pydantic Task
    """
    task: Task = {
        "id": str_to_uuid(proto_task.id) or UUID(int=0),
        "context_id": str_to_uuid(proto_task.context_id) or UUID(int=0),
        "kind": proto_task.kind or "task",
        "status": proto_to_task_status(proto_task.status),
        "artifacts": [proto_to_artifact(artifact) for artifact in proto_task.artifacts],
        "history": [proto_to_message(msg) for msg in proto_task.history],
    }

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
        raise ImportError("Protobuf code not generated. Run: python scripts/generate_proto.py")

    proto_artifact = a2a_pb2.Artifact()
    proto_artifact.artifact_id = uuid_to_str(artifact.get("artifact_id"))
    proto_artifact.name = artifact.get("name", "")

    if "parts" in artifact:
        for part in artifact["parts"]:
            proto_part = part_to_proto(part)
            proto_artifact.parts.append(proto_part)

    if "metadata" in artifact and artifact["metadata"]:
        proto_artifact.metadata.update({str(k): str(v) for k, v in artifact["metadata"].items()})

    return proto_artifact


def proto_to_artifact(proto_artifact: Any) -> Artifact:
    """Convert protobuf Artifact to Pydantic Artifact.

    Args:
        proto_artifact: Protobuf Artifact

    Returns:
        Pydantic Artifact
    """
    artifact: Artifact = {
        "artifact_id": str_to_uuid(proto_artifact.artifact_id) or UUID(int=0),
        "name": proto_artifact.name or "",
        "parts": [proto_to_part(part) for part in proto_artifact.parts],
    }

    if proto_artifact.metadata:
        artifact["metadata"] = dict(proto_artifact.metadata)

    if proto_artifact.name:
        artifact["name"] = proto_artifact.name

    return artifact

