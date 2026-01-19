"""Database operation utilities for PostgreSQL storage."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB

from .serialization import serialize_for_jsonb


def get_current_utc_timestamp() -> datetime:
    """Get current UTC timestamp.

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(timezone.utc)


def prepare_jsonb_value(data: Any) -> Any:
    """Prepare data for JSONB storage.

    Serializes data and casts to JSONB type for SQLAlchemy.

    Args:
        data: Data to prepare for JSONB storage

    Returns:
        SQLAlchemy JSONB cast expression
    """
    serialized = serialize_for_jsonb(data)
    return cast(serialized, JSONB)


def create_update_values(
    state: str | None = None,
    metadata: dict[str, Any] | None = None,
    include_timestamp: bool = True,
) -> dict[str, Any]:
    """Create update values dictionary for task updates.

    Args:
        state: Optional new state value
        metadata: Optional metadata to include
        include_timestamp: Whether to include updated_at timestamp (default: True)

    Returns:
        Dictionary of update values for SQLAlchemy update statement
    """
    values = {}

    if state is not None:
        now = get_current_utc_timestamp()
        values["state"] = state
        values["state_timestamp"] = now
        values["updated_at"] = now
    elif include_timestamp:
        values["updated_at"] = get_current_utc_timestamp()

    return values
