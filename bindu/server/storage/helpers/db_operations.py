from datetime import datetime, timezone
from typing import Any

from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB

from .serialization import serialize_for_jsonb


def get_current_utc_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def prepare_jsonb_value(data: Any) -> Any:
    serialized = serialize_for_jsonb(data)
    return cast(serialized, JSONB)


def create_update_values(
    state: str | None = None,
    metadata: dict[str, Any] | None = None,
    include_timestamp: bool = True
) -> dict[str, Any]:
    values = {}
    
    if state is not None:
        now = get_current_utc_timestamp()
        values["state"] = state
        values["state_timestamp"] = now
        values["updated_at"] = now
    elif include_timestamp:
        values["updated_at"] = get_current_utc_timestamp()
    
    return values
