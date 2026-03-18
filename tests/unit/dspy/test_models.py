"""Unit tests for bindu.dspy.models module.

Tests cover:
- RawTaskData model creation and attributes
- Interaction model creation and attributes
- Frozen dataclass behavior of Interaction
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from bindu.dspy.models import RawTaskData, Interaction


class TestRawTaskData:
    """Test suite for RawTaskData model."""

    def test_raw_task_data_creation(self):
        """Test creating a RawTaskData instance."""
        task_id = uuid4()
        history = [{"role": "user", "content": "Hello"}]
        created_at = datetime.now()

        task = RawTaskData(
            id=task_id,
            history=history,
            created_at=created_at,
        )

        assert task.id == task_id
        assert task.history == history
        assert task.created_at == created_at
        assert task.feedback_data is None

    def test_raw_task_data_with_feedback(self):
        """Test RawTaskData with feedback data."""
        task_id = uuid4()
        history = [{"role": "user", "content": "Test"}]
        feedback = {"rating": 5, "comment": "Good"}

        task = RawTaskData(
            id=task_id,
            history=history,
            created_at=datetime.now(),
            feedback_data=feedback,
        )

        assert task.feedback_data == feedback
        assert task.feedback_data["rating"] == 5

    def test_raw_task_data_empty_history(self):
        """Test RawTaskData with empty history."""
        task = RawTaskData(
            id=uuid4(),
            history=[],
            created_at=datetime.now(),
        )

        assert task.history == []

    def test_raw_task_data_complex_history(self):
        """Test RawTaskData with complex message history."""
        hist = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
            {"role": "assistant", "content": "Answer 2"},
        ]

        task = RawTaskData(
            id=uuid4(),
            history=hist,
            created_at=datetime.now(),
        )

        assert len(task.history) == 5


class TestInteraction:
    """Test suite for Interaction model."""

    def test_interaction_creation_minimal(self):
        """Test creating a minimal Interaction instance."""
        interaction_id = uuid4()
        interaction = Interaction(
            id=interaction_id,
            user_input="Test input",
            agent_output="Test output",
        )

        assert interaction.id == interaction_id
        assert interaction.user_input == "Test input"
        assert interaction.agent_output == "Test output"
        assert interaction.feedback_score is None
        assert interaction.feedback_type is None
        assert interaction.system_prompt is None

    def test_interaction_creation_full(self):
        """Test creating an Interaction with all fields."""
        interaction_id = uuid4()
        interaction = Interaction(
            id=interaction_id,
            user_input="User query",
            agent_output="Agent response",
            feedback_score=0.95,
            feedback_type="rating",
            system_prompt="You are helpful",
        )

        assert interaction.id == interaction_id
        assert interaction.user_input == "User query"
        assert interaction.agent_output == "Agent response"
        assert interaction.feedback_score == 0.95
        assert interaction.feedback_type == "rating"
        assert interaction.system_prompt == "You are helpful"

    def test_interaction_frozen_prevents_modification(self):
        """Test that Interaction is frozen and cannot be modified."""
        interaction = Interaction(
            id=uuid4(),
            user_input="Input",
            agent_output="Output",
        )

        # Frozen dataclass should prevent attribute assignment
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            interaction.user_input = "Modified"

    def test_interaction_feedback_score_types(self):
        """Test Interaction with different feedback score values."""
        tests = [
            (0.0, "Perfect score: 0.0"),
            (0.5, "Average score: 0.5"),
            (1.0, "Perfect score: 1.0"),
            (None, "No feedback"),
        ]

        for score, description in tests:
            interaction = Interaction(
                id=uuid4(),
                user_input="Input",
                agent_output="Output",
                feedback_score=score,
                feedback_type="rating" if score is not None else None,
            )
            assert interaction.feedback_score == score

    def test_interaction_feedback_type_values(self):
        """Test Interaction with different feedback type values."""
        types = ["rating", "thumbs_up", "custom_type", None]

        for feedback_type in types:
            interaction = Interaction(
                id=uuid4(),
                user_input="Input",
                agent_output="Output",
                feedback_type=feedback_type,
            )
            assert interaction.feedback_type == feedback_type

    def test_interaction_empty_strings(self):
        """Test Interaction with empty strings."""
        interaction = Interaction(
            id=uuid4(),
            user_input="",
            agent_output="",
            system_prompt="",
        )

        assert interaction.user_input == ""
        assert interaction.agent_output == ""
        assert interaction.system_prompt == ""

    def test_interaction_multiline_text(self):
        """Test Interaction with multiline text."""
        input_text = "Line 1\nLine 2\nLine 3"
        output_text = "Output Line 1\nOutput Line 2"

        interaction = Interaction(
            id=uuid4(),
            user_input=input_text,
            agent_output=output_text,
        )

        assert "\n" in interaction.user_input
        assert "\n" in interaction.agent_output

    def test_interaction_uuid_type(self):
        """Test that Interaction stores UUID correctly."""
        interaction_id = UUID("12345678-1234-5678-1234-567812345678")
        interaction = Interaction(
            id=interaction_id,
            user_input="Input",
            agent_output="Output",
        )

        assert interaction.id == interaction_id
        assert isinstance(interaction.id, UUID)
