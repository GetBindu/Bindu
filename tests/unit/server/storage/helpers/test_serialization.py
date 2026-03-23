"""Tests for storage serialization helpers."""

from uuid import uuid4

from bindu.server.storage.helpers.serialization import serialize_for_jsonb


class TestSerialization:
    """Test serialization helper functions."""

    def test_serialize_uuid(self):
        """Test serializing UUID to string."""
        test_uuid = uuid4()

        result = serialize_for_jsonb(test_uuid)

        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_serialize_dict_with_uuids(self):
        """Test serializing dict containing UUIDs."""
        test_uuid = uuid4()
        data = {"id": test_uuid, "name": "test"}

        result = serialize_for_jsonb(data)

        assert isinstance(result, dict)
        assert isinstance(result["id"], str)
        assert result["id"] == str(test_uuid)
        assert result["name"] == "test"

    def test_serialize_list_with_uuids(self):
        """Test serializing list containing UUIDs."""
        uuid1 = uuid4()
        uuid2 = uuid4()
        data = [uuid1, uuid2, "string"]

        result = serialize_for_jsonb(data)

        assert isinstance(result, list)
        assert result[0] == str(uuid1)
        assert result[1] == str(uuid2)
        assert result[2] == "string"

    def test_serialize_nested_structure(self):
        """Test serializing nested dict/list with UUIDs."""
        test_uuid = uuid4()
        data = {
            "tasks": [{"id": test_uuid, "status": "pending"}],
            "count": 1,
        }

        result = serialize_for_jsonb(data)

        assert isinstance(result["tasks"][0]["id"], str)
        assert result["tasks"][0]["id"] == str(test_uuid)
        assert result["count"] == 1

    def test_serialize_primitive_types(self):
        """Test serializing primitive types."""
        assert serialize_for_jsonb("string") == "string"
        assert serialize_for_jsonb(123) == 123
        assert serialize_for_jsonb(True) is True
        assert serialize_for_jsonb(None) is None
