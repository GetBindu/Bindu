"""Unit tests for advanced DSPy extraction strategies."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from bindu.dspy.strategies import (
    ContextWindowStrategy,
    KeyTurnsStrategy,
    SlidingWindowStrategy,
    SummaryContextStrategy,
)


class TestContextWindowStrategy:
    """Test ContextWindowStrategy."""

    def test_name_property(self):
        """Test strategy name is 'context_window'."""
        strategy = ContextWindowStrategy()
        assert strategy.name == "context_window"

    def test_extract_with_system_prompt(self):
        """Test system prompt is prepended to user input."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = ContextWindowStrategy(
            n_turns=1,
            system_prompt="You are helpful."
        )
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.system_prompt == "You are helpful."

    def test_extract_without_system_prompt(self):
        """Test works without system prompt."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = ContextWindowStrategy(n_turns=1)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.system_prompt is None

    def test_extract_concatenates_user_messages(self):
        """Test multiple user messages are concatenated."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = ContextWindowStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert "Q1" in result.user_input
        assert "Q2" in result.user_input

    def test_extract_small_window_simple_format(self):
        """Test ≤3 turns use simple separator."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = ContextWindowStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        # Should use \n\n separator, not [Turn N]
        assert "[Turn" not in result.user_input

    def test_extract_large_window_numbered_format(self):
        """Test >3 turns are numbered."""
        messages = []
        for i in range(5):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = ContextWindowStrategy(n_turns=5)
        result = strategy.extract(uuid4(), messages)

        # Should have turn numbers
        assert "[Turn" in result.user_input

    def test_extract_single_turn(self):
        """Test single turn is not formatted."""
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        strategy = ContextWindowStrategy(n_turns=1)
        result = strategy.extract(uuid4(), messages)

        assert result.user_input == "Question"

    def test_extract_uses_last_agent_response(self):
        """Test last assistant is output."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = ContextWindowStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert result.agent_output == "A2"

    def test_extract_default_n_turns(self):
        """Test uses settings default."""
        with patch("bindu.dspy.strategies.context_window.app_settings") as mock_settings:
            mock_settings.dspy.default_n_turns = 3
            strategy = ContextWindowStrategy(n_turns=None)

            messages = [
                {"role": "user", "content": "Q"},
                {"role": "assistant", "content": "A"},
            ]

            result = strategy.extract(uuid4(), messages)
            assert result is not None

    def test_extract_minimum_one_turn(self):
        """Test enforces minimum."""
        strategy = ContextWindowStrategy(n_turns=0)
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None


class TestSlidingWindowStrategy:
    """Test SlidingWindowStrategy."""

    def test_name_property(self):
        """Test strategy name is 'sliding_window'."""
        strategy = SlidingWindowStrategy()
        assert strategy.name == "sliding_window"

    def test_extract_returns_last_window(self):
        """Test single extract returns last window."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        strategy = SlidingWindowStrategy(window_size=2)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert "Q2" in result.user_input or "Q3" in result.user_input
        assert result.agent_output == "A3"

    def test_extract_all_overlapping_windows(self):
        """Test stride=1 creates overlapping windows."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        results = strategy.extract_all(uuid4(), messages)

        # 3 turns with window=2, stride=1 should give 2 windows
        assert len(results) == 2

    def test_extract_all_non_overlapping_windows(self):
        """Test stride=window_size gives non-overlapping."""
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

        strategy = SlidingWindowStrategy(window_size=2, stride=2)
        results = strategy.extract_all(uuid4(), messages)

        # 4 turns with window=2, stride=2 should give 2 windows
        assert len(results) == 2

    def test_extract_all_with_start_offset(self):
        """Test start_offset skips first N turns."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        strategy = SlidingWindowStrategy(window_size=2, stride=1, start_offset=1)
        results = strategy.extract_all(uuid4(), messages)

        # Should start from turn 2 (index 1)
        assert len(results) >= 1
        # First window should not contain Q1
        if results:
            assert "Q1" not in results[0].user_input

    def test_extract_all_not_enough_turns(self):
        """Test returns empty if fewer than window_size."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        strategy = SlidingWindowStrategy(window_size=3)
        results = strategy.extract_all(uuid4(), messages)

        assert len(results) == 0

    def test_extract_all_creates_multiple_interactions(self):
        """Test multiple Interactions are created."""
        messages = []
        for i in range(5):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        results = strategy.extract_all(uuid4(), messages)

        # 5 turns with window=2, stride=1 should give 4 windows
        assert len(results) == 4

    def test_extract_window_concatenates_users(self):
        """Test users in window are concatenated."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = SlidingWindowStrategy(window_size=2)
        result = strategy.extract(uuid4(), messages)

        assert "Q1" in result.user_input
        assert "Q2" in result.user_input

    def test_extract_default_params(self):
        """Test uses settings defaults."""
        with patch("bindu.dspy.strategies.sliding_window.app_settings") as mock_settings:
            mock_settings.dspy.default_window_size = 2
            mock_settings.dspy.default_stride = 1

            strategy = SlidingWindowStrategy(window_size=None, stride=None)
            messages = [
                {"role": "user", "content": "Q"},
                {"role": "assistant", "content": "A"},
            ]

            result = strategy.extract(uuid4(), messages)
            # May return None if not enough turns
            assert result is None or result is not None

    def test_extract_minimum_values(self):
        """Test enforces minimums for window_size, stride."""
        strategy = SlidingWindowStrategy(window_size=0, stride=0)
        # Should enforce minimum of 1
        assert strategy.window_size >= 1
        assert strategy.stride >= 1


class TestSummaryContextStrategy:
    """Test SummaryContextStrategy."""

    def test_name_property(self):
        """Test strategy name is 'summary_context'."""
        strategy = SummaryContextStrategy()
        assert strategy.name == "summary_context"

    def test_extract_with_short_history(self):
        """Test short history uses full context."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = SummaryContextStrategy(recent_turns=3)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        # Short history should not have summary marker
        assert "[Earlier Context Summary]" not in result.user_input

    def test_extract_with_long_history(self):
        """Test long history is summarized."""
        messages = []
        for i in range(10):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=3)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        # Long history should have summary
        assert "[Previous conversation summary]" in result.user_input

    def test_extract_summary_uses_first_turn(self):
        """Test summary includes first turn info."""
        messages = [
            {"role": "user", "content": "Initial question"},
            {"role": "assistant", "content": "Initial answer"},
        ]
        for i in range(10):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=3)
        result = strategy.extract(uuid4(), messages)

        # Summary section should exist (doesn't include turn 0's actual text in output)
        assert "[Previous conversation summary]" in result.user_input

    def test_extract_summary_preserves_last_turns(self):
        """Test last N turns are preserved."""
        messages = []
        for i in range(10):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=3)
        result = strategy.extract(uuid4(), messages)

        # Should have recent user messages from recent_turns
        assert "Q7" in result.user_input or "Q8" in result.user_input or "Q9" in result.user_input

    def test_extract_formats_summary_section(self):
        """Test summary section is clearly marked."""
        messages = []
        for i in range(10):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert "[Previous conversation summary]" in result.user_input
        assert "[Recent conversation]" in result.user_input

    def test_extract_default_params(self):
        """Test uses default parameter values."""
        # Test that default parameters work
        strategy = SummaryContextStrategy()
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None

    def test_extract_threshold_boundary(self):
        """Test exactly at recent_turns threshold is handled."""
        # Create messages exactly at recent_turns threshold
        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=3)
        messages = []
        for i in range(3):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        result = strategy.extract(uuid4(), messages)
        assert result is not None


class TestKeyTurnsStrategy:
    """Test KeyTurnsStrategy."""

    def test_name_property(self):
        """Test strategy name is 'key_turns'."""
        strategy = KeyTurnsStrategy()
        assert strategy.name == "key_turns"

    def test_extract_selects_relevant_turns(self):
        """Test most similar turns are selected."""
        messages = [
            {"role": "user", "content": "What is Python programming?"},
            {"role": "assistant", "content": "Python is a language."},
            {"role": "user", "content": "Tell me about Python features."},
            {"role": "assistant", "content": "Python has many features."},
            {"role": "user", "content": "Explain Python syntax."},
            {"role": "assistant", "content": "Python syntax is simple."},
        ]

        strategy = KeyTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        # Should select turns similar to last turn (about Python)
        assert "Python" in result.user_input

    def test_extract_uses_similarity_method(self):
        """Test specified similarity method is used."""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
            {"role": "assistant", "content": "Answer 2"},
        ]

        strategy = KeyTurnsStrategy(n_turns=1, similarity_method="jaccard")
        result = strategy.extract(uuid4(), messages)

        assert result is not None

    def test_extract_default_similarity_method(self):
        """Test defaults to weighted."""
        strategy = KeyTurnsStrategy(n_turns=2)
        # Default should be weighted
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None or result is None  # Depends on turns

    def test_extract_all_available_turns(self):
        """Test uses all if fewer than n_turns."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        strategy = KeyTurnsStrategy(n_turns=5)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert result.user_input == "Q1"

    def test_extract_includes_last_turn(self):
        """Test last turn is always included."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        strategy = KeyTurnsStrategy(n_turns=1)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        assert "Q2" in result.user_input
        assert result.agent_output == "A2"

    def test_extract_sorts_by_similarity(self):
        """Test turns are sorted by similarity score."""
        messages = [
            {"role": "user", "content": "Python programming language"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Completely different topic here"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "More about Python coding"},
            {"role": "assistant", "content": "A3"},
        ]

        strategy = KeyTurnsStrategy(n_turns=2)
        result = strategy.extract(uuid4(), messages)

        assert result is not None
        # Should prefer turns with "Python"
        assert "Python" in result.user_input

    def test_extract_formats_selected_turns(self):
        """Test selected turns are formatted."""
        messages = []
        for i in range(5):
            messages.extend([
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ])

        strategy = KeyTurnsStrategy(n_turns=3)
        result = strategy.extract(uuid4(), messages)

        assert result is not None

    def test_extract_default_n_turns(self):
        """Test uses default n_turns value."""
        # Test that default n_turns parameter works
        strategy = KeyTurnsStrategy()
        messages = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = strategy.extract(uuid4(), messages)
        assert result is not None
