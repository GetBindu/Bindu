"""Unit tests for DSPy interaction extraction.

This module tests:
- Message cleaning (extractor.py)
- Interaction extraction with strategies (extractor.py)
"""

import pytest
from uuid import uuid4

from bindu.dspy.extractor import clean_messages, InteractionExtractor
from bindu.dspy.models import Interaction
from bindu.dspy.strategies import LastTurnStrategy


# =============================================================================
# Message Cleaning Tests
# =============================================================================


class TestCleanMessages:
    """Test message cleaning functionality."""

    def test_clean_messages_removes_empty_content(self):
        """Test removal of messages with empty content."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Are you there?"},
            {"role": "assistant", "content": "Yes!"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 3
        assert cleaned[0]["content"] == "Hello"
        assert cleaned[1]["content"] == "Are you there?"
        assert cleaned[2]["content"] == "Yes!"

    def test_clean_messages_removes_missing_content(self):
        """Test removal of messages without content field."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant"},  # No content field
            {"role": "user", "content": "Test"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "Hello"
        assert cleaned[1]["content"] == "Test"

    def test_clean_messages_whitespace_trimming(self):
        """Test whitespace trimming."""
        history = [
            {"role": "user", "content": "  Hello  "},
            {"role": "assistant", "content": "\n\nWorld\n\n"},
            {"role": "user", "content": "   "},  # Only whitespace - should be removed
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "Hello"
        assert cleaned[1]["content"] == "World"

    def test_clean_messages_removes_non_dict_entries(self):
        """Test removal of non-dict entries."""
        history = [
            {"role": "user", "content": "Hello"},
            "invalid_entry",
            None,
            {"role": "assistant", "content": "Hi"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "Hello"
        assert cleaned[1]["content"] == "Hi"

    def test_clean_messages_removes_no_role(self):
        """Test removal of messages without role."""
        history = [
            {"role": "user", "content": "Hello"},
            {"content": "No role"},  # Missing role field
            {"role": "assistant", "content": "Hi"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["role"] == "user"
        assert cleaned[1]["role"] == "assistant"

    def test_clean_messages_empty_history(self):
        """Test cleaning empty history."""
        cleaned = clean_messages([])
        assert len(cleaned) == 0

    def test_clean_messages_preserves_valid_messages(self):
        """Test that valid messages are preserved exactly."""
        history = [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is artificial intelligence."},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0] == {"role": "user", "content": "What is AI?"}
        assert cleaned[1] == {"role": "assistant", "content": "AI is artificial intelligence."}

    def test_clean_messages_converts_content_to_string(self):
        """Test that content is converted to string."""
        history = [
            {"role": "user", "content": 123},  # Number
            {"role": "assistant", "content": True},  # Boolean
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "123"
        assert cleaned[1]["content"] == "True"


# =============================================================================
# InteractionExtractor Tests
# =============================================================================


class TestInteractionExtractor:
    """Test InteractionExtractor class."""

    def test_extractor_initialization_default_strategy(self):
        """Test initialization with default strategy."""
        extractor = InteractionExtractor()
        assert isinstance(extractor.strategy, LastTurnStrategy)

    def test_extractor_initialization_custom_strategy(self):
        """Test initialization with custom strategy."""
        custom_strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy=custom_strategy)
        assert extractor.strategy is custom_strategy

    def test_extract_with_last_turn_strategy(self):
        """Test extraction with LastTurnStrategy."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(
            task_id=task_id,
            history=history,
            feedback_score=0.8,
            feedback_type="rating",
        )

        assert interaction is not None
        assert interaction.id == task_id
        # LastTurnStrategy should extract only the last user-assistant pair
        assert interaction.user_input == "Second question"
        assert interaction.agent_output == "Second answer"
        assert interaction.feedback_score == 0.8
        assert interaction.feedback_type == "rating"

    def test_extract_with_empty_history(self):
        """Test extraction with empty history."""
        task_id = uuid4()
        history = []

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is None

    def test_extract_with_invalid_history(self):
        """Test extraction with invalid history (no valid messages)."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": ""},  # Empty content
            {"role": "assistant"},  # No content
            {"content": "No role"},  # No role
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is None

    def test_extract_cleans_messages_automatically(self):
        """Test that extraction automatically cleans messages."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "  Question  "},  # Extra whitespace
            {"role": "assistant", "content": ""},  # Should be removed
            {"role": "assistant", "content": "  Answer  "},  # Extra whitespace
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is not None
        # Messages should be cleaned (trimmed)
        assert interaction.user_input == "Question"
        assert interaction.agent_output == "Answer"

    def test_extract_without_feedback(self):
        """Test extraction without feedback."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is not None
        assert interaction.feedback_score is None
        assert interaction.feedback_type is None

    def test_extract_all_single_interaction(self):
        """Test extract_all with single interaction strategy."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interactions = extractor.extract_all(
            task_id=task_id,
            history=history,
            feedback_score=0.9,
        )

        assert len(interactions) == 1
        assert interactions[0].user_input == "Question"
        assert interactions[0].agent_output == "Answer"
        assert interactions[0].feedback_score == 0.9

    def test_extract_all_empty_history(self):
        """Test extract_all with empty history."""
        task_id = uuid4()
        history = []

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interactions = extractor.extract_all(task_id=task_id, history=history)

        assert len(interactions) == 0

    def test_extract_all_delegates_to_strategy(self):
        """Test that extract_all delegates to strategy's extract_all method."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        # Create a mock strategy that returns multiple interactions
        class MultipleInteractionStrategy:
            @property
            def name(self):
                return "test_multiple"

            def extract(self, task_id, messages, feedback_score=None, feedback_type=None):
                # This shouldn't be called by extract_all
                return None

            def extract_all(self, task_id, messages, feedback_score=None, feedback_type=None):
                # Return multiple interactions
                return [
                    Interaction(
                        id=task_id,
                        user_input="Q1",
                        agent_output="A1",
                        feedback_score=feedback_score,
                    ),
                    Interaction(
                        id=task_id,
                        user_input="Q2",
                        agent_output="A2",
                        feedback_score=feedback_score,
                    ),
                ]

        extractor = InteractionExtractor(strategy=MultipleInteractionStrategy())
        interactions = extractor.extract_all(
            task_id=task_id,
            history=history,
            feedback_score=0.7,
        )

        assert len(interactions) == 2
        assert interactions[0].user_input == "Q1"
        assert interactions[1].user_input == "Q2"
        assert all(i.feedback_score == 0.7 for i in interactions)

    def test_extract_handles_incomplete_conversations(self):
        """Test extraction with incomplete conversation (no assistant response)."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question without answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        # LastTurnStrategy should return None if there's no complete turn
        assert interaction is None

    def test_extract_preserves_task_id(self):
        """Test that task_id is preserved in extracted interaction."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Test question"},
            {"role": "assistant", "content": "Test answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is not None
        assert interaction.id == task_id

    def test_extract_with_multi_turn_conversation(self):
        """Test extraction with multi-turn conversation."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "Who created it?"},
            {"role": "assistant", "content": "Guido van Rossum created Python."},
            {"role": "user", "content": "When was it created?"},
            {"role": "assistant", "content": "Python was first released in 1991."},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is not None
        # LastTurnStrategy extracts only the last turn
        assert interaction.user_input == "When was it created?"
        assert interaction.agent_output == "Python was first released in 1991."

    def test_extract_with_system_messages_ignored(self):
        """Test that system messages don't interfere with extraction."""
        task_id = uuid4()
        history = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        assert interaction is not None
        # System message should be ignored by LastTurnStrategy
        assert interaction.user_input == "Hello"
        assert interaction.agent_output == "Hi there!"


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestExtractorEdgeCases:
    """Test edge cases and error handling."""

    def test_extract_with_none_history(self):
        """Test extraction with None history."""
        task_id = uuid4()
        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        
        # Should handle gracefully
        interaction = extractor.extract(task_id=task_id, history=None)
        assert interaction is None

    def test_extract_with_malformed_messages(self):
        """Test extraction with malformed messages."""
        task_id = uuid4()
        history = [
            "not a dict",
            {"role": "user"},  # No content
            {"content": "No role"},  # No role
            {"role": "user", "content": "Valid question"},
            {"role": "assistant", "content": "Valid answer"},
        ]

        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        interaction = extractor.extract(task_id=task_id, history=history)

        # Should extract the valid messages
        assert interaction is not None
        assert interaction.user_input == "Valid question"
        assert interaction.agent_output == "Valid answer"

    def test_extract_all_with_none_history(self):
        """Test extract_all with None history."""
        task_id = uuid4()
        extractor = InteractionExtractor(strategy=LastTurnStrategy())
        
        interactions = extractor.extract_all(task_id=task_id, history=None)
        assert len(interactions) == 0
