"""Minimal tests for storage validation helpers."""

import pytest
from uuid import UUID, uuid4

from bindu.server.storage.helpers.validation import validate_uuid_type


class TestValidation:
    """Test validation helper functions."""

    def test_validate_uuid_type_with_uuid(self):
        """Test validating UUID object."""
        test_uuid = uuid4()

        result = validate_uuid_type(test_uuid, "test_param")

        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_validate_uuid_type_with_string(self):
        """Test validating valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        result = validate_uuid_type(uuid_str, "test_param")

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_validate_uuid_type_with_none_raises(self):
        """Test that None raises TypeError."""
        with pytest.raises(TypeError, match="cannot be None"):
            validate_uuid_type(None, "test_param")

    def test_validate_uuid_type_with_invalid_string_raises(self):
        """Test that invalid UUID string raises TypeError."""
        with pytest.raises(TypeError, match="must be a valid UUID string"):
            validate_uuid_type("not-a-uuid", "test_param")

    def test_validate_uuid_type_with_invalid_type_raises(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError, match="must be UUID or str"):
            validate_uuid_type(123, "test_param")  # type: ignore
