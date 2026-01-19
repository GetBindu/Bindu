from typing import Any
from uuid import UUID


def serialize_for_jsonb(obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_jsonb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_jsonb(item) for item in obj]
    else:
        return obj
