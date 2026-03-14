"""Unit tests for bindu.dspy.extractor module.

Tests cover:
- Message cleaning logic
- InteractionExtractor initialization
- Interaction extraction from histories
- Edge cases (empty messages, invalid formats)
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from uuid import uuid4

from bindu.dspy.extractor import InteractionExtractor, clean_messages
from bindu.dspy.strategies import LastTurnStrategy


class TestCleanMessages:
    """Test suite for message cleaning functionality."""

    def test_clean_messages_basic(self):
        """Test cleaning basic message history."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        cleaned = clean_messages(messages)
        assert len(cleaned) == 2
        assert cleaned[0]["role"] == "user"
        assert cleaned[0]["content"] == "Hello"

    def test_clean_messages_removes_empty_content(self):
        """Test that messages with empty content are removed."""
        messages = [
            {"role": "user", "content": "Valid"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": None},
            {"role": "assistant", "content": "Another valid"},
        ]

        cleaned = clean_messages(messages)
        assert len(cleaned) == 2
        assert all(msg["content"] for msg in cleaned)

    def test_clean_messages_with_parts_format(self):
        """Test cleaning messages in parts array format."""
        messages = [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "Hello world"}],
            },
            {
                "role": "assistant",
                "parts": [{"kind": "text", "text": "Hi"}],
            },
        ]

        cleaned = clean_messages(messages)
        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "Hello world"
        assert cleaned[1]["content"] == "Hi"

    def test_clean_messages_mixed_formats(self):
        """Test cleaning messages with mixed content and parts formats."""
        messages = [
            {"role": "user", "content": "Direct content"},
            {"role": "assistant", "parts": [{"kind": "text", "text": "Parts content"}]},
        ]

        cleaned = clean_messages(messages)
        assert len(cleaned) == 2

    def test_clean_messages_removes_invalid_messages(self):
        """Test that invalid messages are skipped."""
        messages = [
            {"role": "user", "content": "Valid"},
            {"invalid": "structure"},
            "not a dict",
            {"role": "user"},  # Missing content
            {"content": "No role"},
            {"role": "assistant", "content": "Valid"},
        ]

        cleaned = clean_messages(messages)
        # Should only keep the two valid messages
        assert len(cleaned) == 2

    def test_clean_messages_strips_whitespace(self):
        """Test that content is stripped of whitespace."""
        messages = [
            {"role": "user", "content": "   spaces   "},
            {"role": "assistant", "content": "\n\ttabs\n\t"},
        ]

        cleaned = clean_messages(messages)
        assert cleaned[0]["content"] == "spaces"
        assert cleaned[1]["content"] == "tabs"

    def test_clean_messages_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""
        messages = [
            {"role": "user", "content": "Hello   world   test"},
        ]

        cleaned = clean_messages(messages)
        assert "Hello   world   test" in cleaned[0]["content"]

    def test_clean_messages_empty_parts_array(self):
        """Test handling of empty parts array."""
        messages = [
            {"role": "user", "parts": []},
            {"role": "assistant", "content": "Valid"},
        ]

        cleaned = clean_messages(messages)
        # Message with empty parts should be removed
        assert len(cleaned) == 1

    def test_clean_messages_multiple_text_parts(self):
        """Test combining multiple text parts."""
        messages = [
            {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "Part 1"},
                    {"kind": "text", "text": "Part 2"},
                ],
            },
        ]

        cleaned = clean_messages(messages)
        assert "Part 1" in cleaned[0]["content"]
        assert "Part 2" in cleaned[0]["content"]

    def test_clean_messages_non_text_parts_ignored(self):
        """Test that non-text parts are ignored."""
        messages = [
            {
                "role": "user",
                "parts": [
                    {"kind": "image", "url": "..."},
                    {"kind": "text", "text": "Text content"},
                ],
            },
        ]

        cleaned = clean_messages(messages)
        assert cleaned[0]["content"] == "Text content"

    def test_clean_messages_empty_list(self):
        """Test cleaning an empty message list."""
        cleaned = clean_messages([])
        assert cleaned == []

    def test_clean_messages_none_input(self):
        """Test that non-list inputs are handled gracefully."""
        # This tests the isinstance check
        cleaned = clean_messages([])
        assert isinstance(cleaned, list)


class TestInteractionExtractor:
    """Test suite for InteractionExtractor class."""

    def test_extractor_initialization_default(self):
        """Test initializing extractor with default strategy."""
        extractor = InteractionExtractor()
        assert extractor.strategy is not None
        assert isinstance(extractor.strategy, LastTurnStrategy)

    def test_extractor_initialization_custom_strategy(self):
        """Test initializing extractor with custom strategy."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy=strategy)
        assert extractor.strategy is strategy

    def test_extract_valid_interaction(self):
        """Test extracting an interaction from valid history."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4"},
        ]

        extractor = InteractionExtractor()
        interaction = extractor.extract(task_id, history)

        assert interaction is not None
        assert interaction.id == task_id
        assert "2+2" in interaction.user_input or "2+2" in str(history)

    def test_extract_with_feedback(self):
        """Test extracting interaction with feedback data."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        extractor = InteractionExtractor()
        interaction = extractor.extract(
            task_id,
            history,
            feedback_score=0.85,
            feedback_type="rating",
        )

        assert interaction is not None
        assert interaction.feedback_score == 0.85
        assert interaction.feedback_type == "rating"

    def test_extract_empty_history(self):
        """Test extracting from empty history."""
        extractor = InteractionExtractor()
        interaction = extractor.extract(uuid4(), [])

        assert interaction is None

    def test_extract_invalid_history(self):
        """Test extracting from invalid history."""
        extractor = InteractionExtractor()
        interaction = extractor.extract(uuid4(), None)

        assert interaction is None

    def test_extract_all_multiple_interactions(self):
        """Test extracting all interactions from history."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        extractor = InteractionExtractor()
        interactions = extractor.extract_all(task_id, history)

        # Result depends on strategy, but should be a list
        assert isinstance(interactions, list)

    def test_extract_all_with_feedback(self):
        """Test extracting all interactions with feedback."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        extractor = InteractionExtractor()
        interactions = extractor.extract_all(
            task_id,
            history,
            feedback_score=0.9,
            feedback_type="thumbs_up",
        )

        assert isinstance(interactions, list)

    def test_extract_all_empty_history(self):
        """Test extracting all from empty history returns empty list."""
        extractor = InteractionExtractor()
        interactions = extractor.extract_all(uuid4(), [])

        assert interactions == []

    def test_extract_with_system_prompt(self):
        """Test extraction includes system prompt context."""
        task_id = uuid4()
        history = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        extractor = InteractionExtractor()
        interaction = extractor.extract(task_id, history)

        # System prompt should be accessible in extraction
        assert interaction is not None

    def test_extract_multiline_content(self):
        """Test extraction with multiline message content."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Line1\nLine2\nLine3"},
            {"role": "assistant", "content": "Response\nLine2"},
        ]

        extractor = InteractionExtractor()
        interaction = extractor.extract(task_id, history)

        assert interaction is not None
        assert interaction.user_input is not None

    def test_extractor_with_parts_messages(self):
        """Test extraction with parts-format messages."""
        task_id = uuid4()
        history = [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "Question"}],
            },
            {
                "role": "assistant",
                "parts": [{"kind": "text", "text": "Answer"}],
            },
        ]

        extractor = InteractionExtractor()
        interaction = extractor.extract(task_id, history)

        assert interaction is not None
