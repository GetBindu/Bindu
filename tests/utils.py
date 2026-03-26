"""Test utilities for creating test data and assertions."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from bindu.common.protocol.types import (
    Artifact,
    Context,
    Message,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)


def create_test_message(
    message_id: UUID | None = None,
    context_id: UUID | None = None,
    task_id: UUID | None = None,
    role: str = "user",
    text: str = "Test message",
    reference_task_ids: list[UUID] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """Create a test Message object with sensible defaults."""
    text_part = cast(
        TextPart,
        {
            "kind": "text",
            "text": text,
        },
    )

    message = cast(
        Message,
        {
            "message_id": message_id or uuid4(),
            "context_id": context_id or uuid4(),
            "task_id": task_id or uuid4(),
            "kind": "message",
            "parts": [text_part],
            "role": role,
        },
    )

    if reference_task_ids:
        message["reference_task_ids"] = reference_task_ids

    if metadata:
        message["metadata"] = metadata

    return message


def create_test_task(
    task_id: UUID | None = None,
    context_id: UUID | None = None,
    state: TaskState = "submitted",
    message: Message | None = None,
    artifacts: list[Artifact] | None = None,
    history: list[Message] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Task:
    """Create a test Task object with sensible defaults."""
    tid = task_id or uuid4()
    cid = context_id or uuid4()

    status = cast(
        TaskStatus,
        {
            "state": state,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    if message:
        status["message"] = message

    task = cast(
        Task,
        {
            "id": tid,
            "context_id": cid,
            "kind": "task",
            "status": status,
        },
    )

    if artifacts:
        task["artifacts"] = artifacts

    if history:
        task["history"] = history

    if metadata:
        task["metadata"] = metadata

    return task


def create_test_artifact(
    artifact_id: UUID | None = None,
    name: str = "test_artifact",
    text: str = "Test artifact content",
    metadata: dict[str, Any] | None = None,
) -> Artifact:
    """Create a test Artifact object."""
    text_part = cast(
        TextPart,
        {
            "kind": "text",
            "text": text,
        },
    )

    artifact = cast(
        Artifact,
        {
            "artifact_id": artifact_id or uuid4(),
            "name": name,
            "parts": [text_part],
        },
    )

    if metadata:
        artifact["metadata"] = metadata

    return artifact


def create_test_context(
    context_id: UUID | None = None,
    tasks: list[UUID] | None = None,
    name: str = "Test Context",
    role: str = "user",
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> Context:
    """Create a test Context object."""
    now = datetime.now(UTC).isoformat()

    context = cast(
        Context,
        {
            "context_id": context_id or uuid4(),
            "kind": "context",
            "role": role,
            "created_at": now,
            "updated_at": now,
        },
    )

    if tasks:
        context["tasks"] = tasks

    if name:
        context["name"] = name

    if status:
        context["status"] = status  # type: ignore

    if metadata:
        context["metadata"] = metadata

    return context


def assert_task_state(task: Task, expected_state: TaskState) -> None:
    """Assert that a task is in the expected state."""
    actual_state = task["status"]["state"]
    assert actual_state == expected_state, f"Expected task state '{expected_state}', got '{actual_state}'"


def assert_jsonrpc_error(response: dict[str, Any], expected_code: int) -> None:
    """Assert that a JSON-RPC response contains an error with the expected code."""
    assert "error" in response, "Response does not contain an error"
    assert "code" in response["error"], "Error does not contain a code"
    actual_code = response["error"]["code"]
    assert actual_code == expected_code, f"Expected error code {expected_code}, got {actual_code}"


def assert_jsonrpc_success(response: dict[str, Any]) -> None:
    """Assert that a JSON-RPC response is successful."""
    assert "result" in response, "Response does not contain a result"
    assert "error" not in response, f"Response contains an error: {response.get('error')}"


def get_deterministic_uuid(seed: int) -> UUID:
    """Generate a deterministic UUID for testing."""
    # Create a UUID from a deterministic seed
    hex_str = f"{seed:032x}"
    return UUID(hex_str)
