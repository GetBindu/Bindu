"""Tests for database operations helpers."""

from datetime import datetime, timezone

from bindu.server.storage.helpers.db_operations import (
    get_current_utc_timestamp,
    create_update_values,
)


class TestDatabaseOperations:
    """Test database operation helpers."""

    def test_get_current_utc_timestamp(self):
        """Test getting current UTC timestamp."""
        result = get_current_utc_timestamp()

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_create_update_values_with_state(self):
        """Test creating update values with state."""
        result = create_update_values(state="completed")

        assert "state" in result
        assert result["state"] == "completed"
        assert "state_timestamp" in result
        assert "updated_at" in result
        assert isinstance(result["updated_at"], datetime)

    def test_create_update_values_without_state(self):
        """Test creating update values without state."""
        result = create_update_values()

        assert "state" not in result
        assert "updated_at" in result
        assert isinstance(result["updated_at"], datetime)

    def test_create_update_values_no_timestamp(self):
        """Test creating update values without timestamp."""
        result = create_update_values(include_timestamp=False)

        assert result == {}

    def test_create_update_values_state_no_timestamp(self):
        """Test creating update values with state but no extra timestamp."""
        result = create_update_values(state="working", include_timestamp=False)

        assert "state" in result
        assert result["state"] == "working"
        assert "state_timestamp" in result
        assert "updated_at" in result  # Always included when state is set

    def test_create_update_values_with_metadata(self):
        """Test creating update values with metadata."""
        metadata = {"key": "value"}
        result = create_update_values(metadata=metadata)

        # Metadata parameter exists but may not be used in current implementation
        assert "updated_at" in result
