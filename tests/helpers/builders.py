"""Test data builders using fluent API pattern.

These builders make it easy to create test data with sensible defaults
while allowing customization of specific fields.
"""

from typing import Any
from uuid import UUID, uuid4


class TaskBuilder:
    """Builder for creating test Task objects.

    Example:
        task = TaskBuilder().with_state("working").with_context_id("ctx-123").build()
    """

    def __init__(self):
        """Initialize TaskBuilder with default values."""
        self._data: dict[str, Any] = {
            "id": str(uuid4()),
            "context_id": str(uuid4()),
            "state": "submitted",
            "history": [],
            "artifacts": [],
        }

    def with_id(self, task_id: str) -> "TaskBuilder":
        """Set the task ID."""
        self._data["id"] = task_id
        return self

    def with_context_id(self, context_id: str) -> "TaskBuilder":
        """Set the context ID."""
        self._data["context_id"] = context_id
        return self

    def with_state(self, state: str) -> "TaskBuilder":
        """Set the task state."""
        self._data["state"] = state
        return self

    def with_history(self, history: list) -> "TaskBuilder":
        """Set the message history."""
        self._data["history"] = history
        return self

    def with_artifacts(self, artifacts: list) -> "TaskBuilder":
        """Set the artifacts."""
        self._data["artifacts"] = artifacts
        return self

    def build(self) -> dict[str, Any]:
        """Build the task dictionary."""
        return dict(self._data)


class MessageBuilder:
    """Builder for creating test Message objects.

    Example:
        msg = MessageBuilder().with_text("Hello").with_role("user").build()
    """

    def __init__(self):
        """Initialize MessageBuilder with default values."""
        self._data: dict[str, Any] = {
            "id": str(uuid4()),
            "context_id": str(uuid4()),
            "role": "user",
            "parts": [],
        }

    def with_id(self, message_id: str) -> "MessageBuilder":
        """Set the message ID."""
        self._data["id"] = message_id
        return self

    def with_context_id(self, context_id: str) -> "MessageBuilder":
        """Set the context ID."""
        self._data["context_id"] = context_id
        return self

    def with_role(self, role: str) -> "MessageBuilder":
        """Set the message role."""
        self._data["role"] = role
        return self

    def with_text(self, text: str) -> "MessageBuilder":
        """Add a text part to the message."""
        self._data["parts"].append({"text": text})
        return self

    def with_parts(self, parts: list) -> "MessageBuilder":
        """Set the message parts."""
        self._data["parts"] = parts
        return self

    def build(self) -> dict[str, Any]:
        """Build the message dictionary."""
        return dict(self._data)


class ContextBuilder:
    """Builder for creating test Context objects.

    Example:
        ctx = ContextBuilder().with_id("ctx-123").with_metadata({"key": "value"}).build()
    """

    def __init__(self, context_id: UUID | None = None):
        """Initialize ContextBuilder with optional context ID."""
        self._data: dict[str, Any] = {
            "id": str(context_id or uuid4()),
            "metadata": {},
        }

    def with_id(self, context_id: str) -> "ContextBuilder":
        """Set the context ID."""
        self._data["id"] = context_id
        return self

    def with_metadata(self, metadata: dict) -> "ContextBuilder":
        """Set the context metadata."""
        self._data["metadata"] = metadata
        return self

    def build(self) -> dict[str, Any]:
        """Build the context dictionary."""
        return dict(self._data)


class ArtifactBuilder:
    """Builder for creating test Artifact objects.

    Example:
        artifact = ArtifactBuilder().with_text("Result").with_mime_type("text/plain").build()
    """

    def __init__(self, artifact_id: str | None = None):
        """Initialize ArtifactBuilder with optional artifact ID."""
        self._data: dict[str, Any] = {
            "id": artifact_id or str(uuid4()),
            "parts": [],
        }

    def with_id(self, artifact_id: str) -> "ArtifactBuilder":
        """Set the artifact ID."""
        self._data["id"] = artifact_id
        return self

    def with_text(self, text: str, mime_type: str = "text/plain") -> "ArtifactBuilder":
        """Add a text part to the artifact."""
        self._data["parts"].append(
            {
                "text": text,
                "mimeType": mime_type,
            }
        )
        return self

    def with_parts(self, parts: list) -> "ArtifactBuilder":
        """Set the artifact parts."""
        self._data["parts"] = parts
        return self

    def build(self) -> dict[str, Any]:
        """Build the artifact dictionary."""
        return dict(self._data)
