"""JSONB serialization utilities for PostgreSQL storage."""

from typing import Any
from uuid import UUID


def serialize_for_jsonb(obj: Any) -> Any:
    """Recursively serialize objects for JSONB storage.

    Converts UUID objects to strings for PostgreSQL JSONB compatibility.

    Args:
        obj: Object to serialize (dict, list, UUID, or primitive)

    Returns:
        Serialized object with UUIDs converted to strings
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_jsonb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_jsonb(item) for item in obj]
    else:
        return obj
