"""Unit tests for bindu.dspy.context module.

Tests cover:
- Context variable creation and retrieval
- Setting and getting prompt IDs
- Clearing context
- Multiple context operations
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from bindu.dspy.context import set_prompt_id, get_prompt_id, clear_prompt_id, current_prompt_id


class TestContextVariables:
    """Test suite for async context variables."""

    def test_initial_context_value(self):
        """Test that context variable has initial default value."""
        # Reset to default first
        clear_prompt_id()
        value = get_prompt_id()
        assert value is None

    def test_set_and_get_prompt_id(self):
        """Test setting and getting a prompt ID."""
        prompt_id = "test-prompt-123"
        set_prompt_id(prompt_id)

        retrieved = get_prompt_id()
        assert retrieved == prompt_id

    def test_set_prompt_id_overwrites(self):
        """Test that setting a new prompt ID overwrites the previous one."""
        set_prompt_id("first-id")
        assert get_prompt_id() == "first-id"

        set_prompt_id("second-id")
        assert get_prompt_id() == "second-id"

    def test_clear_prompt_id(self):
        """Test clearing the prompt ID."""
        set_prompt_id("some-id")
        assert get_prompt_id() == "some-id"

        clear_prompt_id()
        assert get_prompt_id() is None

    def test_set_none_clears_context(self):
        """Test that setting None clears the context."""
        set_prompt_id("test-id")
        assert get_prompt_id() == "test-id"

        set_prompt_id(None)
        assert get_prompt_id() is None

    def test_uuid_string_prompt_id(self):
        """Test with UUID-formatted prompt ID."""
        uuid_prompt_id = "550e8400-e29b-41d4-a716-446655440000"
        set_prompt_id(uuid_prompt_id)

        assert get_prompt_id() == uuid_prompt_id

    def test_long_prompt_id(self):
        """Test with longer prompt ID string."""
        long_id = "a" * 1000
        set_prompt_id(long_id)

        assert get_prompt_id() == long_id

    def test_special_chars_in_prompt_id(self):
        """Test with special characters in prompt ID."""
        special_id = "prompt-id-with_special.chars@123"
        set_prompt_id(special_id)

        assert get_prompt_id() == special_id

    def test_empty_string_prompt_id(self):
        """Test setting empty string as prompt ID."""
        set_prompt_id("")
        # Empty string should be stored (not treated as None)
        assert get_prompt_id() == ""

    def test_multiple_set_operations(self):
        """Test multiple sequential set operations."""
        ids = ["id1", "id2", "id3", "id4", "id5"]

        for prompt_id in ids:
            set_prompt_id(prompt_id)
            assert get_prompt_id() == prompt_id

    def test_clear_and_set_sequence(self):
        """Test sequence of clear and set operations."""
        set_prompt_id("id1")
        clear_prompt_id()
        assert get_prompt_id() is None

        set_prompt_id("id2")
        assert get_prompt_id() == "id2"

        clear_prompt_id()
        assert get_prompt_id() is None

    def test_context_var_type(self):
        """Test that context variable is of correct type."""
        # current_prompt_id should be a ContextVar
        assert hasattr(current_prompt_id, "get")
        assert hasattr(current_prompt_id, "set")
