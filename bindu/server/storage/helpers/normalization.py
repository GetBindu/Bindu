"""UUID and message normalization utilities for storage operations."""

from uuid import UUID

from bindu.common.protocol.types import Message

from .validation import validate_uuid_type


def normalize_uuid(value: UUID | str | None, param_name: str = "uuid") -> UUID:
    """Normalize a UUID value to UUID type.

    Args:
        value: UUID value to normalize (UUID, string, or None)
        param_name: Parameter name for error messages (default: "uuid")

    Returns:
        UUID: Normalized UUID object

    Raises:
        TypeError: If value is invalid
    """
    return validate_uuid_type(value, param_name)


def normalize_message_uuids(
    message: Message, task_id: UUID | None = None, context_id: UUID | None = None
) -> Message:
    """Normalize all UUID fields in a message to UUID type.

    Converts string UUIDs to UUID objects for task_id, context_id,
    message_id, and reference_task_ids fields.

    Args:
        message: Message to normalize
        task_id: Optional task_id to set (overrides message value)
        context_id: Optional context_id to set (overrides message value)

    Returns:
        Message: Message with normalized UUID fields

    Raises:
        TypeError: If any UUID field has invalid value
    """
    if task_id is not None:
        message["task_id"] = task_id
    elif "task_id" in message:
        message["task_id"] = normalize_uuid(message["task_id"], "task_id")

    if context_id is not None:
        message["context_id"] = context_id
    elif "context_id" in message:
        message["context_id"] = normalize_uuid(message["context_id"], "context_id")

    if "message_id" in message and message["message_id"] is not None:
        message["message_id"] = normalize_uuid(message["message_id"], "message_id")

    if "reference_task_ids" in message and message["reference_task_ids"] is not None:
        message["reference_task_ids"] = [
            normalize_uuid(ref_id, "reference_task_id")
            for ref_id in message["reference_task_ids"]
        ]

    return message
