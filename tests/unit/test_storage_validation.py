"""Tests for storage validation utilities."""

import pytest
from uuid import UUID
from bindu.server.storage.helpers.validation import validate_uuid_type


class TestValidateUUIDType:
    """Test UUID validation."""

    def test_validate_uuid_object(self):
        """Test validating UUID object."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        result = validate_uuid_type(test_uuid, "test_param")
        assert result == test_uuid

    def test_validate_uuid_string(self):
        """Test validating UUID string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = validate_uuid_type(uuid_str, "test_param")
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_validate_none_value(self):
        """Test that None raises TypeError."""
        with pytest.raises(TypeError, match="test_param cannot be None"):
            validate_uuid_type(None, "test_param")

    def test_validate_invalid_uuid_string(self):
        """Test that invalid UUID string raises TypeError."""
        with pytest.raises(TypeError, match="must be a valid UUID string"):
            validate_uuid_type("invalid-uuid", "test_param")

    def test_validate_invalid_type(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError, match="must be UUID or str"):
            validate_uuid_type(123, "test_param")  # type: ignore[arg-type]
