"""Unit tests for basic DSPy extraction strategies."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from bindu.dspy.strategies import (
    STRATEGIES,
    BaseExtractionStrategy,
    FirstNTurnsStrategy,
    FullHistoryStrategy,
    LastNTurnsStrategy,
    LastTurnStrategy,
    get_strategy,
    parse_turns,
)


class TestStrategyRegistry:
    """Test strategy registry and factory function."""

    def test_all_strategies_registered(self):
        """Test that all expected strategies are registered."""
        assert "last_turn" in STRATEGIES
        assert "full_history" in STRATEGIES
        assert "last_n_turns" in STRATEGIES
        assert "first_n_turns" in STRATEGIES
        assert "context_window" in STRATEGIES
        assert "sliding_window" in STRATEGIES
        assert "summary_context" in STRATEGIES
        assert "key_turns" in STRATEGIES

    def test_get_strategy_last_turn(self):
        """Test factory creates LastTurnStrategy."""
        strategy = get_strategy("last_turn")
        assert isinstance(strategy, LastTurnStrategy)
        assert strategy.name == "last_turn"

    def test_get_strategy_full_history(self):
        """Test factory creates FullHistoryStrategy."""
        strategy = get_strategy("full_history")
        assert isinstance(strategy, FullHistoryStrategy)
        assert strategy.name == "full_history"

    def test_get_strategy_with_params(self):
        """Test factory passes params to strategy constructor."""
        strategy = get_strategy("context_window", n_turns=5, system_prompt="Be helpful")
        assert strategy.name == "context_window"

    def test_get_strategy_unknown_raises_error(self):
        """Test unknown name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("invalid_strategy_name")

    def test_get_strategy_lists_available(self):
        """Test error message lists available strategies."""
        try:
            get_strategy("invalid")
        except ValueError as e:
            assert "last_turn" in str(e)
            assert "full_history" in str(e)


class TestParseTurns:
    """Test parse_turns utility function."""

    def test_parse_turns_single_exchange(self):
        """Test one user-assistant pair is parsed."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 1
        assert turns[0] == ("Hello", "Hi there!")

    def test_parse_turns_multiple_exchanges(self):
        """Test multiple pairs are parsed in order."""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
            {"role": "assistant", "content": "Answer 2"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 2
        assert turns[0] == ("Question 1", "Answer 1")
        assert turns[1] == ("Question 2", "Answer 2")

    def test_parse_turns_skips_incomplete(self):
        """Test user without assistant is skipped."""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
            # No assistant response
        ]

        turns = parse_turns(messages)
        assert len(turns) == 1
        assert turns[0] == ("Question 1", "Answer 1")

    def test_parse_turns_handles_agent_role(self):
        """Test 'agent' role is treated like 'assistant'."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "agent", "content": "Hi!"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 1
        assert turns[0] == ("Hello", "Hi!")

    def test_parse_turns_consecutive_users(self):
        """Test only last user before assistant is used."""
        messages = [
            {"role": "user", "content": "First user"},
            {"role": "user", "content": "Second user"},
            {"role": "assistant", "content": "Response"},
        ]

        turns = parse_turns(messages)
        assert len(turns) == 1
        assert turns[0] == ("Second user", "Response")

    def test_parse_turns_empty_messages(self):
        """Test empty list returns empty list."""
        turns = parse_turns([])
        assert turns == []

    def test_parse_turns_no_complete_pairs(self):
        """Test only user messages returns empty."""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "user", "content": "Question 2"},
        ]

        turns = parse_turns(messages)
        assert turns == []


class TestLastTurnStrategy:
    """Test LastTurnStrategy."""

    def test_name_property(self):
        """Test strategy name is 'last_turn'."""
        strategy = LastTurnStrategy()
        assert strategy.name == "last_turn"

    def test_extract_last_turn_success(self):
        """Test last user-assistant pair is extracted."""
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]

        strategy = LastTurnStrategy()
        task_id = uuid4()
        result = strategy.extract(task_id, messages)

        assert result is not None
        assert result.user_input == "Second question"
        assert result.agent_output == "Second answer"
        assert result.id == task_id

    def test_extract_with_multiple_turns(self):
        """Test only last turn is extracted."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        strategy = LastTurnStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result.user_input == "Q3"
        assert result.agent_output == "A3"

    def test_extract_no_assistant_message(self):
        """Test returns None if no assistant message."""
        messages = [
            {"role": "user", "content": "Question"},
        ]

        strategy = LastTurnStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is None

    def test_extract_no_user_message(self):
        """Test returns None if no user message."""
        messages = [
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = LastTurnStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is None

    def test_extract_includes_feedback(self):
        """Test feedback score and type are included."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = LastTurnStrategy()
        result = strategy.extract(
            uuid4(),
            messages,
            feedback_score=0.95,
            feedback_type="rating",
        )

        assert result.feedback_score == 0.95
        assert result.feedback_type == "rating"

    def test_extract_handles_agent_role(self):
        """Test works with 'agent' instead of 'assistant'."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "agent", "content": "Answer"},
        ]

        strategy = LastTurnStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.agent_output == "Answer"


class TestFullHistoryStrategy:
    """Test FullHistoryStrategy."""

    def test_name_property(self):
        """Test strategy name is 'full_history'."""
        strategy = FullHistoryStrategy()
        assert strategy.name == "full_history"

    def test_extract_first_user_all_assistants(self):
        """Test first user + all assistants concatenated."""
        messages = [
            {"role": "user", "content": "Initial question"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Follow-up"},
            {"role": "assistant", "content": "Second response"},
        ]

        strategy = FullHistoryStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.user_input == "Initial question"
        assert "First response" in result.agent_output
        assert "Second response" in result.agent_output

    def test_extract_formats_multiple_responses(self):
        """Test multiple responses are formatted with roles."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "More"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "More"},
            {"role": "assistant", "content": "Response 3"},
        ]

        strategy = FullHistoryStrategy()
        result = strategy.extract(uuid4(), messages)

        # Should have role-prefixed responses
        assert "Assistant: Response 1" in result.agent_output
        assert "Assistant: Response 2" in result.agent_output
        assert "Assistant: Response 3" in result.agent_output

    def test_extract_single_turn(self):
        """Test single turn includes role prefix."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = FullHistoryStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result.agent_output == "Assistant: Answer"
        assert "[Response" not in result.agent_output

    def test_extract_respects_max_length(self):
        """Test returns None if exceeds max_full_history_length."""
        # Create very long message
        long_response = "x" * 15000
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": long_response},
        ]

        strategy = FullHistoryStrategy()
        with patch("bindu.dspy.strategies.full_history.app_settings") as mock_settings:
            mock_settings.dspy.max_full_history_length = 10000
            result = strategy.extract(uuid4(), messages)

            # Implementation returns None when exceeding max length
            assert result is None

    def test_extract_no_assistant_messages(self):
        """Test returns None if no assistants."""
        messages = [
            {"role": "user", "content": "Question"},
        ]

        strategy = FullHistoryStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is None

    def test_extract_no_user_message(self):
        """Test returns None if no user."""
        messages = [
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = FullHistoryStrategy()
        result = strategy.extract(uuid4(), messages)

        assert result is None


class TestFirstNTurnsStrategy:
    """Test FirstNTurnsStrategy."""

    def test_name_property(self):
        """Test strategy name is 'first_n_turns'."""
        strategy = FirstNTurnsStrategy(n_turns=3)
        assert strategy.name == "first_n_turns"

    def test_extract_first_n_turns(self):
        """Test first N turns are extracted."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        strategy = FirstNTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        # First user message is the input
        assert result.user_input == "Q1"
        # agent_output contains formatted conversation with Q2
        assert "Q2" in result.agent_output
        assert "A1" in result.agent_output
        assert "A2" in result.agent_output
        assert "Q3" not in result.agent_output

    def test_extract_fewer_turns_available(self):
        """Test uses all available if less than N."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        strategy = FirstNTurnsStrategy(n_turns=5)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.user_input == "Q1"
        assert result.agent_output == "A1"

    def test_extract_formats_user_messages(self):
        """Test first user is input, subsequent users in agent_output."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = FirstNTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        # First user message is the input
        assert result.user_input == "Q1"
        # Q2 should be in the formatted agent_output
        assert "Q2" in result.agent_output

    def test_extract_uses_last_assistant(self):
        """Test agent_output includes all assistants in formatted conversation."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = FirstNTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        # agent_output includes the formatted conversation
        assert "A1" in result.agent_output
        assert "A2" in result.agent_output
        assert "Assistant: A1" in result.agent_output
        assert "Assistant: A2" in result.agent_output

    def test_extract_default_n_turns(self):
        """Test uses app_settings.default_n_turns if None."""
        with patch("bindu.dspy.strategies.first_n_turns.app_settings") as mock_settings:
            mock_settings.dspy.default_n_turns = 3
            strategy = FirstNTurnsStrategy(n_turns=None)

            messages = [
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"},
            ]

            result = strategy.extract(uuid4(), messages)
            assert result is not None

    def test_extract_minimum_one_turn(self):
        """Test n_turns < 1 is treated as 1."""
        strategy = FirstNTurnsStrategy(n_turns=0)
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None

    def test_extract_no_complete_turns(self):
        """Test returns None if no complete turns."""
        strategy = FirstNTurnsStrategy(n_turns=2)
        messages = [
            {"role": "user", "content": "Question"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is None


class TestLastNTurnsStrategy:
    """Test LastNTurnsStrategy."""

    def test_name_property(self):
        """Test strategy name is 'last_n_turns'."""
        strategy = LastNTurnsStrategy(n_turns=3)
        assert strategy.name == "last_n_turns"

    def test_extract_last_n_turns(self):
        """Test last N turns are extracted."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        strategy = LastNTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert "Q3" in result.user_input
        assert "Q4" in result.user_input
        assert "Q1" not in result.user_input
        assert result.agent_output == "A4"

    def test_extract_fewer_turns_available(self):
        """Test uses all available if less than N."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        strategy = LastNTurnsStrategy(n_turns=5)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.user_input == "Q1"

    def test_extract_formats_user_messages(self):
        """Test multiple users are formatted correctly."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = LastNTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert "Q1" in result.user_input
        assert "Q2" in result.user_input

    def test_extract_single_turn(self):
        """Test single turn is not numbered."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = LastNTurnsStrategy(n_turns=1)
        result = strategy.extract(uuid4(), messages)

        assert result.user_input == "Question"
        assert "\n" not in result.user_input

    def test_extract_default_n_turns(self):
        """Test uses app_settings default."""
        with patch("bindu.dspy.strategies.last_n_turns.app_settings") as mock_settings:
            mock_settings.dspy.default_n_turns = 3
            strategy = LastNTurnsStrategy(n_turns=None)

            messages = [
                {"role": "user", "content": "Q"},
                {"role": "assistant", "content": "A"},
            ]

            result = strategy.extract(uuid4(), messages)
            assert result is not None

    def test_extract_minimum_one_turn(self):
        """Test enforces minimum of 1."""
        strategy = LastNTurnsStrategy(n_turns=-5)
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None
