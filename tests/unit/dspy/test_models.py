"""Unit tests for DSPy data models."""

from uuid import uuid4

import pytest

from bindu.dspy.models import Interaction, PromptCandidate
from bindu.dspy.dataset import RawTaskData


class TestInteraction:
    """Test Interaction dataclass."""

    def test_interaction_creation_with_all_fields(self):
        """Test creating Interaction with all fields."""
        task_id = uuid4()
        interaction = Interaction(
            id=task_id,
            user_input="What is Python?",
            agent_output="Python is a programming language.",
            feedback_score=0.85,
            feedback_type="rating",
            system_prompt="You are a helpful assistant.",
        )

        assert interaction.id == task_id
        assert interaction.user_input == "What is Python?"
        assert interaction.agent_output == "Python is a programming language."
        assert interaction.feedback_score == 0.85
        assert interaction.feedback_type == "rating"
        assert interaction.system_prompt == "You are a helpful assistant."

    def test_interaction_creation_minimal(self):
        """Test creating Interaction with only required fields."""
        task_id = uuid4()
        interaction = Interaction(
            id=task_id,
            user_input="Hello",
            agent_output="Hi there!",
        )

        assert interaction.id == task_id
        assert interaction.user_input == "Hello"
        assert interaction.agent_output == "Hi there!"
        assert interaction.feedback_score is None
        assert interaction.feedback_type is None
        assert interaction.system_prompt is None

    def test_interaction_is_frozen(self):
        """Test that Interaction dataclass is immutable."""
        interaction = Interaction(
            id=uuid4(),
            user_input="Test",
            agent_output="Response",
        )

        with pytest.raises(AttributeError):
            interaction.user_input = "Modified"

    def test_interaction_without_feedback(self):
        """Test creating Interaction with feedback_score=None."""
        interaction = Interaction(
            id=uuid4(),
            user_input="Question",
            agent_output="Answer",
            feedback_score=None,
            feedback_type=None,
        )

        assert interaction.feedback_score is None
        assert interaction.feedback_type is None

    def test_interaction_equality(self):
        """Test that two Interactions with same data are equal."""
        task_id = uuid4()
        interaction1 = Interaction(
            id=task_id,
            user_input="Test",
            agent_output="Response",
            feedback_score=0.9,
            feedback_type="rating",
        )
        interaction2 = Interaction(
            id=task_id,
            user_input="Test",
            agent_output="Response",
            feedback_score=0.9,
            feedback_type="rating",
        )

        assert interaction1 == interaction2


class TestPromptCandidate:
    """Test PromptCandidate dataclass."""

    def test_prompt_candidate_creation(self):
        """Test creating PromptCandidate successfully."""
        candidate = PromptCandidate(
            text="You are a helpful AI assistant.",
            metadata={"score": 0.95, "iterations": 10},
        )

        assert candidate.text == "You are a helpful AI assistant."
        assert candidate.metadata == {"score": 0.95, "iterations": 10}

    def test_prompt_candidate_with_metadata(self):
        """Test creating PromptCandidate with various metadata."""
        metadata = {
            "optimizer": "SIMBA",
            "training_examples": 100,
            "validation_score": 0.92,
            "created_at": "2026-01-28",
        }
        candidate = PromptCandidate(
            text="System prompt text",
            metadata=metadata,
        )

        assert candidate.text == "System prompt text"
        assert candidate.metadata["optimizer"] == "SIMBA"
        assert candidate.metadata["training_examples"] == 100
        assert candidate.metadata["validation_score"] == 0.92

    def test_prompt_candidate_is_frozen(self):
        """Test that PromptCandidate is immutable."""
        candidate = PromptCandidate(
            text="Original text",
            metadata={"key": "value"},
        )

        with pytest.raises(AttributeError):
            candidate.text = "Modified text"


class TestRawTaskData:
    """Test RawTaskData dataclass."""

    def test_raw_task_data_creation(self):
        """Test creating RawTaskData with all fields."""
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        feedback_data = {"rating": 5}

        raw_task = RawTaskData(
            id=task_id,
            history=history,
            created_at="2026-01-28T00:00:00Z",
            feedback_data=feedback_data,
        )

        assert raw_task.id == task_id
        assert raw_task.history == history
        assert raw_task.created_at == "2026-01-28T00:00:00Z"
        assert raw_task.feedback_data == feedback_data

    def test_raw_task_data_without_feedback(self):
        """Test creating RawTaskData without feedback_data."""
        task_id = uuid4()
        raw_task = RawTaskData(
            id=task_id,
            history=[{"role": "user", "content": "Test"}],
            created_at="2026-01-28T00:00:00Z",
        )

        assert raw_task.id == task_id
        assert raw_task.feedback_data is None

    def test_raw_task_data_with_empty_history(self):
        """Test creating RawTaskData with empty history list."""
        task_id = uuid4()
        raw_task = RawTaskData(
            id=task_id,
            history=[],
            created_at="2026-01-28T00:00:00Z",
            feedback_data=None,
        )

        assert raw_task.id == task_id
        assert raw_task.history == []
        assert raw_task.feedback_data is None
