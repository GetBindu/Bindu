"""Unit tests for bindu.dspy.strategies module.

Tests cover:
- Base strategy implementation
- Extraction strategy interface
- Turn parsing functionality
- Strategy error handling
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock

from bindu.dspy.strategies.base import BaseExtractionStrategy, parse_turns
from bindu.dspy.strategies.last_turn import LastTurnStrategy
from bindu.dspy.models import Interaction


class TestParseTurns:
    """Test suite for turn parsing utility."""

    def test_parse_turns_basic(self):
        """Test parsing basic user-assistant turns."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Q1", "A1")

    def test_parse_turns_multiple(self):
        """Test parsing multiple turns."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 2
        assert turns[0] == ("Q1", "A1")
        assert turns[1] == ("Q2", "A2")

    def test_parse_turns_agent_role(self):
        """Test that 'agent' role is treated as assistant."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "agent", "content": "A1"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Q1", "A1")

    def test_parse_turns_case_insensitive(self):
        """Test that role matching is case-insensitive."""
        messages = [
            {"role": "USER", "content": "Q1"},
            {"role": "ASSISTANT", "content": "A1"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1

    def test_parse_turns_missing_assistant(self):
        """Test that orphaned user messages are skipped."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Q2", "A2")

    def test_parse_turns_system_messages_ignored(self):
        """Test that system messages are ignored."""
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Q1", "A1")

    def test_parse_turns_empty(self):
        """Test parsing empty message list."""
        turns = parse_turns([])
        assert turns == []

    def test_parse_turns_only_user(self):
        """Test parsing with only user messages."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "user", "content": "Q2"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 0

    def test_parse_turns_only_assistant(self):
        """Test parsing with only assistant messages."""
        messages = [
            {"role": "assistant", "content": "A1"},
            {"role": "assistant", "content": "A2"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 0

    def test_parse_turns_no_role(self):
        """Test messages without role field."""
        messages = [
            {"content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        turns = parse_turns(messages)
        # Message without role should be skipped


class TestLastTurnStrategy:
    """Test suite for LastTurnStrategy."""

    def test_strategy_name(self):
        """Test strategy name property."""
        strategy = LastTurnStrategy()
        assert strategy.name == "last_turn"

    def test_extract_basic_two_turn(self):
        """Test extracting last turn from two-turn conversation."""
        strategy = LastTurnStrategy()
        task_id = uuid4()
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        interaction = strategy.extract(task_id, messages)

        assert interaction is not None
        assert interaction.user_input == "Question"
        assert interaction.agent_output == "Answer"
        assert interaction.id == task_id

    def test_extract_ignores_earlier_turns(self):
        """Test that only last turn is extracted."""
        strategy = LastTurnStrategy()
        task_id = uuid4()
        messages = [
            {"role": "user", "content": "Old Q"},
            {"role": "assistant", "content": "Old A"},
            {"role": "user", "content": "New Q"},
            {"role": "assistant", "content": "New A"},
        ]

        interaction = strategy.extract(task_id, messages)

        assert interaction.user_input == "New Q"
        assert interaction.agent_output == "New A"

    def test_extract_with_feedback(self):
        """Test extracting with feedback data."""
        strategy = LastTurnStrategy()
        task_id = uuid4()
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        interaction = strategy.extract(
            task_id,
            messages,
            feedback_score=0.8,
            feedback_type="rating",
        )

        assert interaction.feedback_score == 0.8
        assert interaction.feedback_type == "rating"

    def test_extract_with_system_prompt(self):
        """Test extraction with system prompt in history."""
        strategy = LastTurnStrategy()
        task_id = uuid4()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        interaction = strategy.extract(task_id, messages)

        assert interaction.user_input == "Q"
        assert interaction.agent_output == "A"

    def test_extract_missing_user(self):
        """Test extraction when user message is missing."""
        strategy = LastTurnStrategy()
        messages = [
            {"role": "assistant", "content": "A"},
        ]

        interaction = strategy.extract(uuid4(), messages)
        assert interaction is None

    def test_extract_missing_assistant(self):
        """Test extraction when assistant message is missing."""
        strategy = LastTurnStrategy()
        messages = [
            {"role": "user", "content": "Q"},
        ]

        interaction = strategy.extract(uuid4(), messages)
        assert interaction is None

    def test_extract_empty_messages(self):
        """Test extraction with empty messages."""
        strategy = LastTurnStrategy()
        interaction = strategy.extract(uuid4(), [])
        assert interaction is None

    def test_extract_agent_role(self):
        """Test that 'agent' role is treated as assistant."""
        strategy = LastTurnStrategy()
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "agent", "content": "A"},
        ]

        interaction = strategy.extract(uuid4(), messages)
        assert interaction is not None
        assert interaction.agent_output == "A"

    def test_extract_multiline_content(self):
        """Test extraction with multiline content."""
        strategy = LastTurnStrategy()
        question = "Line 1\nLine 2\nLine 3"
        answer = "Answer\nLine 2"

        messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]

        interaction = strategy.extract(uuid4(), messages)

        assert interaction.user_input == question
        assert interaction.agent_output == answer

    def test_is_base_strategy_subclass(self):
        """Test that LastTurnStrategy is a BaseExtractionStrategy."""
        strategy = LastTurnStrategy()
        assert isinstance(strategy, BaseExtractionStrategy)

    def test_extract_returns_interaction_type(self):
        """Test that extract returns Interaction type."""
        strategy = LastTurnStrategy()
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert isinstance(result, Interaction)


class TestBaseExtractionStrategy:
    """Test suite for base strategy."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseExtractionStrategy cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseExtractionStrategy()

    def test_subclass_must_implement_name(self):
        """Test that subclass must implement name property."""

        class IncompleteStrategy(BaseExtractionStrategy):
            def extract(self, task_id, messages, feedback_score=None, feedback_type=None):
                return None

        with pytest.raises(TypeError):
            IncompleteStrategy()

    def test_subclass_must_implement_extract(self):
        """Test that subclass must implement extract method."""

        class IncompleteStrategy(BaseExtractionStrategy):
            @property
            def name(self):
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteStrategy()
