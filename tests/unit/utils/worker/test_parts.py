"""Tests for worker parts utilities."""

from bindu.utils.worker.parts import PartConverter


class TestPartConverter:
    """Test PartConverter functionality."""

    def test_result_to_parts_with_string(self):
        """Test converting string to text part."""
        result = PartConverter.result_to_parts("Hello world")

        assert len(result) == 1
        assert result[0]["kind"] == "text"
        assert result[0]["text"] == "Hello world"

    def test_result_to_parts_with_list_of_strings(self):
        """Test converting list of strings to text parts."""
        result = PartConverter.result_to_parts(["Line 1", "Line 2", "Line 3"])

        assert len(result) == 3
        assert all(p["kind"] == "text" for p in result)
        assert result[0]["text"] == "Line 1"

    def test_result_to_parts_with_dict(self):
        """Test converting dict to data part."""
        data = {"key": "value", "number": 42}
        result = PartConverter.result_to_parts(data)

        assert len(result) == 1
        assert result[0]["kind"] == "data"

    def test_result_to_parts_with_mixed_list(self):
        """Test converting mixed list to parts."""
        data = ["text", {"key": "value"}, 123]
        result = PartConverter.result_to_parts(data)

        assert len(result) == 3
        assert result[0]["kind"] == "text"
        assert result[0]["text"] == "text"

    def test_dict_to_part_with_text_part(self):
        """Test converting dict with text kind."""
        data = {"kind": "text", "text": "Hello"}
        result = PartConverter.dict_to_part(data)

        assert result["kind"] == "text"
        assert result["text"] == "Hello"

    def test_dict_to_part_with_data_part(self):
        """Test converting dict with data kind."""
        data = {"kind": "data", "data": {"key": "value"}, "text": ""}
        result = PartConverter.dict_to_part(data)

        assert result["kind"] == "data"

    def test_result_to_parts_with_empty_list(self):
        """Test converting empty list."""
        result = PartConverter.result_to_parts([])

        assert result == []
