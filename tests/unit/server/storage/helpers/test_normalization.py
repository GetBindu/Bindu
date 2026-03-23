"""Minimal tests for storage normalization helpers."""

from uuid import UUID, uuid4
from typing import cast

from bindu.common.protocol.types import Message
from bindu.server.storage.helpers.normalization import (
    normalize_uuid,
    normalize_message_uuids,
)


class TestNormalization:
    """Test normalization helper functions."""

    def test_normalize_uuid_with_uuid(self):
        """Test normalizing UUID object."""
        test_uuid = uuid4()

        result = normalize_uuid(test_uuid, "test_param")

        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_normalize_uuid_with_string(self):
        """Test normalizing UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        result = normalize_uuid(uuid_str, "test_param")

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_normalize_message_uuids_with_task_id(self):
        """Test normalizing message with task_id override."""
        task_id = uuid4()
        message = cast(Message, {"role": "user", "content": "test"})

        result = normalize_message_uuids(message, task_id=task_id)

        assert result["task_id"] == task_id

    def test_normalize_message_uuids_with_context_id(self):
        """Test normalizing message with context_id override."""
        context_id = uuid4()
        message = cast(Message, {"role": "user", "content": "test"})

        result = normalize_message_uuids(message, context_id=context_id)

        assert result["context_id"] == context_id

    def test_normalize_message_uuids_converts_string_ids(self):
        """Test normalizing message converts string UUIDs."""
        task_id_str = "550e8400-e29b-41d4-a716-446655440000"
        context_id_str = "660e8400-e29b-41d4-a716-446655440000"
        message_id_str = "770e8400-e29b-41d4-a716-446655440000"

        message = cast(
            Message,
            {
                "role": "user",
                "task_id": task_id_str,
                "context_id": context_id_str,
                "message_id": message_id_str,
                "content": "test",
            },
        )

        result = normalize_message_uuids(message)

        assert isinstance(result["task_id"], UUID)
        assert isinstance(result["context_id"], UUID)
        assert isinstance(result["message_id"], UUID)

    def test_normalize_message_uuids_handles_reference_task_ids(self):
        """Test normalizing message with reference_task_ids."""
        ref_id1 = "550e8400-e29b-41d4-a716-446655440000"
        ref_id2 = "660e8400-e29b-41d4-a716-446655440000"

        message = cast(
            Message,
            {
                "role": "user",
                "content": "test",
                "reference_task_ids": [ref_id1, ref_id2],
            },
        )

        result = normalize_message_uuids(message)

        assert len(result["reference_task_ids"]) == 2
        assert all(isinstance(rid, UUID) for rid in result["reference_task_ids"])
