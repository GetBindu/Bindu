"""Unit tests for DSPy dataset pipeline.

This module tests:
- Raw task data fetching (dataset.py)
- Feedback normalization (dataset.py)
- Interaction extraction (dataset.py)
- Validation and deduplication (dataset.py)
- Complete pipeline integration (dataset.py)
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

import dspy

from bindu.dspy.dataset import (
    RawTaskData,
    fetch_raw_task_data,
    normalize_feedback,
    extract_interactions,
    validate_and_clean_interactions,
    deduplicate_interactions,
    prepare_golden_dataset,
    convert_to_dspy_examples,
)
from bindu.dspy.models import Interaction
from bindu.dspy.strategies import LastTurnStrategy


# =============================================================================
# Data Fetching Tests
# =============================================================================


class TestFetchRawTaskData:
    """Test fetching tasks from database."""

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_success(self):
        """Test fetching tasks from database."""
        task_id = uuid4()
        mock_rows = [
            {
                "id": task_id,
                "history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ],
                "created_at": datetime.now(),
                "feedback_data": {"rating": 5},
            }
        ]

        with patch("bindu.dspy.dataset.PostgresStorage") as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=mock_rows)
            mock_storage_class.return_value = mock_storage

            result = await fetch_raw_task_data(limit=10, did="test-did")

            assert len(result) == 1
            assert result[0].id == task_id
            assert len(result[0].history) == 2
            assert result[0].feedback_data == {"rating": 5}

            mock_storage_class.assert_called_once_with(did="test-did")
            mock_storage.connect.assert_called_once()
            mock_storage.fetch_tasks_with_feedback.assert_called_once_with(limit=10)
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_limit_parameter(self):
        """Test limit parameter."""
        with patch("bindu.dspy.dataset.PostgresStorage") as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])
            mock_storage_class.return_value = mock_storage

            await fetch_raw_task_data(limit=50)

            mock_storage.fetch_tasks_with_feedback.assert_called_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_default_limit(self):
        """Test default limit from settings."""
        with patch("bindu.dspy.dataset.PostgresStorage") as mock_storage_class:
            with patch("bindu.dspy.dataset.app_settings") as mock_settings:
                mock_settings.dspy.max_interactions_query_limit = 1000
                mock_storage = AsyncMock()
                mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])
                mock_storage_class.return_value = mock_storage

                await fetch_raw_task_data(limit=None)

                mock_storage.fetch_tasks_with_feedback.assert_called_once_with(limit=1000)

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_connection_error(self):
        """Test connection error handling."""
        with patch("bindu.dspy.dataset.PostgresStorage") as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.connect = AsyncMock(side_effect=Exception("Connection failed"))
            mock_storage_class.return_value = mock_storage

            with pytest.raises(ConnectionError, match="Failed to fetch raw task data"):
                await fetch_raw_task_data()


# =============================================================================
# Feedback Normalization Tests
# =============================================================================


class TestNormalizeFeedback:
    """Test feedback normalization to 0.0-1.0 scale."""

    def test_normalize_rating_valid(self):
        """Test rating (1-5) normalization."""
        # Test all valid ratings
        assert normalize_feedback({"rating": 1}) == (0.2, "rating")
        assert normalize_feedback({"rating": 3}) == (0.6, "rating")
        assert normalize_feedback({"rating": 5}) == (1.0, "rating")
        assert normalize_feedback({"rating": 4.5}) == (0.9, "rating")

    def test_normalize_rating_invalid(self):
        """Test invalid rating values."""
        assert normalize_feedback({"rating": 0}) == (None, None)
        assert normalize_feedback({"rating": 6}) == (None, None)
        assert normalize_feedback({"rating": "invalid"}) == (None, None)

    def test_normalize_thumbs_up_bool(self):
        """Test thumbs_up (true/false) normalization."""
        assert normalize_feedback({"thumbs_up": True}) == (1.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": False}) == (0.0, "thumbs_up")

    def test_normalize_thumbs_up_strings(self):
        """Test thumbs_up string formats."""
        assert normalize_feedback({"thumbs_up": "true"}) == (1.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "True"}) == (1.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "1"}) == (1.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "yes"}) == (1.0, "thumbs_up")

        assert normalize_feedback({"thumbs_up": "false"}) == (0.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "False"}) == (0.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "0"}) == (0.0, "thumbs_up")
        assert normalize_feedback({"thumbs_up": "no"}) == (0.0, "thumbs_up")

    def test_normalize_missing_feedback(self):
        """Test missing/invalid feedback."""
        assert normalize_feedback(None) == (None, None)
        assert normalize_feedback({}) == (None, None)
        assert normalize_feedback({"other_field": "value"}) == (None, None)

    def test_normalize_rating_priority_over_thumbs(self):
        """Test that rating takes priority when both exist."""
        feedback = {"rating": 4, "thumbs_up": False}
        score, feedback_type = normalize_feedback(feedback)
        assert score == 0.8
        assert feedback_type == "rating"


# =============================================================================
# Interaction Extraction Tests
# =============================================================================


class TestExtractInteractions:
    """Test interaction extraction with strategies."""

    def test_extract_interactions_last_turn_strategy(self):
        """Test extraction with LastTurnStrategy."""
        task_id = uuid4()
        raw_tasks = [
            RawTaskData(
                id=task_id,
                history=[
                    {"role": "user", "content": "What is 2+2?"},
                    {"role": "assistant", "content": "4"},
                ],
                created_at=datetime.now(),
                feedback_data={"rating": 5},
            )
        ]

        interactions = extract_interactions(raw_tasks, strategy=LastTurnStrategy())

        assert len(interactions) == 1
        assert interactions[0].id == task_id
        assert interactions[0].user_input == "What is 2+2?"
        assert interactions[0].agent_output == "4"
        assert interactions[0].feedback_score == 1.0
        assert interactions[0].feedback_type == "rating"

    def test_extract_interactions_no_feedback(self):
        """Test extraction without feedback."""
        task_id = uuid4()
        raw_tasks = [
            RawTaskData(
                id=task_id,
                history=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                ],
                created_at=datetime.now(),
                feedback_data=None,
            )
        ]

        interactions = extract_interactions(raw_tasks, strategy=LastTurnStrategy())

        assert len(interactions) == 1
        assert interactions[0].feedback_score is None
        assert interactions[0].feedback_type is None

    def test_extract_interactions_multiple_tasks(self):
        """Test extraction from multiple tasks."""
        raw_tasks = [
            RawTaskData(
                id=uuid4(),
                history=[
                    {"role": "user", "content": "Q1"},
                    {"role": "assistant", "content": "A1"},
                ],
                created_at=datetime.now(),
                feedback_data={"thumbs_up": True},
            ),
            RawTaskData(
                id=uuid4(),
                history=[
                    {"role": "user", "content": "Q2"},
                    {"role": "assistant", "content": "A2"},
                ],
                created_at=datetime.now(),
                feedback_data={"thumbs_up": False},
            ),
        ]

        interactions = extract_interactions(raw_tasks, strategy=LastTurnStrategy())

        assert len(interactions) == 2
        assert interactions[0].feedback_score == 1.0
        assert interactions[1].feedback_score == 0.0

    def test_extract_interactions_empty_tasks(self):
        """Test extraction from empty task list."""
        interactions = extract_interactions([], strategy=LastTurnStrategy())
        assert len(interactions) == 0


# =============================================================================
# Validation and Cleaning Tests
# =============================================================================


class TestValidateAndCleanInteractions:
    """Test interaction validation and cleaning."""

    def test_validate_minimum_length_filtering(self):
        """Test minimum length filtering."""
        task_id = uuid4()
        interactions = [
            Interaction(
                id=task_id,
                user_input="Hi",  # Too short
                agent_output="Hello there! How can I help you today?",
            ),
            Interaction(
                id=task_id,
                user_input="What is the weather like?",
                agent_output="Ok",  # Too short
            ),
            Interaction(
                id=task_id,
                user_input="What is machine learning?",
                agent_output="Machine learning is a branch of AI.",
            ),
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 5
            mock_settings.dspy.min_output_length = 10

            validated = validate_and_clean_interactions(interactions)

            # Only the third interaction should pass
            assert len(validated) == 1
            assert validated[0].user_input == "What is machine learning?"

    def test_validate_whitespace_cleaning(self):
        """Test whitespace cleaning."""
        task_id = uuid4()
        interactions = [
            Interaction(
                id=task_id,
                user_input="  What   is   Python?  ",
                agent_output=" Python   is   a   programming   language. ",
            ),
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 1
            mock_settings.dspy.min_output_length = 1

            validated = validate_and_clean_interactions(interactions)

            assert len(validated) == 1
            assert validated[0].user_input == "What is Python?"
            assert validated[0].agent_output == "Python is a programming language."

    def test_validate_identical_input_output_filtering(self):
        """Test identical input/output filtering."""
        task_id = uuid4()
        interactions = [
            Interaction(
                id=task_id,
                user_input="echo test",
                agent_output="echo test",  # Identical
            ),
            Interaction(
                id=task_id,
                user_input="What is AI?",
                agent_output="AI is artificial intelligence.",
            ),
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 1
            mock_settings.dspy.min_output_length = 1

            validated = validate_and_clean_interactions(interactions)

            # Only the second interaction should pass
            assert len(validated) == 1
            assert validated[0].user_input == "What is AI?"

    def test_validate_empty_list(self):
        """Test validation of empty list."""
        validated = validate_and_clean_interactions([])
        assert len(validated) == 0


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplicateInteractions:
    """Test interaction deduplication."""

    def test_deduplicate_exact_matches(self):
        """Test deduplication based on input/output."""
        task_id1 = uuid4()
        task_id2 = uuid4()

        interactions = [
            Interaction(
                id=task_id1,
                user_input="What is Python?",
                agent_output="Python is a programming language.",
                feedback_score=0.8,
            ),
            Interaction(
                id=task_id2,
                user_input="What is Python?",
                agent_output="Python is a programming language.",
                feedback_score=0.9,  # Different feedback, but same content
            ),
            Interaction(
                id=uuid4(),
                user_input="What is Java?",
                agent_output="Java is a programming language.",
            ),
        ]

        deduplicated = deduplicate_interactions(interactions)

        # Should keep only 2 unique interactions
        assert len(deduplicated) == 2

    def test_deduplicate_keeps_first_occurrence(self):
        """Test that deduplication keeps first occurrence."""
        task_id1 = uuid4()
        task_id2 = uuid4()

        interactions = [
            Interaction(
                id=task_id1,
                user_input="Test",
                agent_output="Response",
                feedback_score=0.5,
            ),
            Interaction(
                id=task_id2,
                user_input="Test",
                agent_output="Response",
                feedback_score=1.0,
            ),
        ]

        deduplicated = deduplicate_interactions(interactions)

        assert len(deduplicated) == 1
        # Should keep the first one (with feedback_score=0.5)
        assert deduplicated[0].id == task_id1
        assert deduplicated[0].feedback_score == 0.5

    def test_deduplicate_empty_list(self):
        """Test deduplication of empty list."""
        deduplicated = deduplicate_interactions([])
        assert len(deduplicated) == 0

    def test_deduplicate_no_duplicates(self):
        """Test when there are no duplicates."""
        interactions = [
            Interaction(id=uuid4(), user_input="Q1", agent_output="A1"),
            Interaction(id=uuid4(), user_input="Q2", agent_output="A2"),
            Interaction(id=uuid4(), user_input="Q3", agent_output="A3"),
        ]

        deduplicated = deduplicate_interactions(interactions)

        assert len(deduplicated) == 3


# =============================================================================
# Complete Pipeline Tests
# =============================================================================


class TestPrepareGoldenDataset:
    """Test golden dataset preparation."""

    def test_prepare_golden_dataset(self):
        """Test preparing dataset in DSPy-ready format."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="What is Python?",
                agent_output="Python is a programming language.",
                feedback_score=0.9,
                feedback_type="rating",
            ),
            Interaction(
                id=uuid4(),
                user_input="What is Java?",
                agent_output="Java is also a programming language.",
                feedback_score=0.8,
                feedback_type="rating",
            ),
        ]

        dataset = prepare_golden_dataset(interactions)

        assert len(dataset) == 2
        assert dataset[0]["input"] == "What is Python?"
        assert dataset[0]["output"] == "Python is a programming language."
        assert dataset[0]["feedback"]["score"] == 0.9
        assert dataset[0]["feedback"]["type"] == "rating"

    def test_prepare_golden_dataset_without_feedback(self):
        """Test preparing dataset without feedback."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Test",
                agent_output="Response",
            ),
        ]

        dataset = prepare_golden_dataset(interactions)

        assert len(dataset) == 1
        assert dataset[0]["feedback"]["score"] is None
        assert dataset[0]["feedback"]["type"] is None


# =============================================================================
# DSPy Conversion Tests
# =============================================================================


class TestConvertToDspyExamples:
    """Test conversion to DSPy Example format."""

    def test_convert_to_dspy_examples(self):
        """Test conversion to DSPy Example format."""
        dataset = [
            {
                "input": "What is Python?",
                "output": "Python is a programming language.",
                "feedback": {"score": 0.9, "type": "rating"},
            },
            {
                "input": "What is Java?",
                "output": "Java is also a programming language.",
                "feedback": {"score": 0.8, "type": "rating"},
            },
        ]

        examples = convert_to_dspy_examples(dataset)

        assert len(examples) == 2
        assert all(isinstance(ex, dspy.Example) for ex in examples)
        assert examples[0].input == "What is Python?"
        assert examples[0].output == "Python is a programming language."
        assert examples[1].input == "What is Java?"

    def test_convert_empty_list(self):
        """Test conversion of empty list."""
        examples = convert_to_dspy_examples([])
        assert len(examples) == 0

    def test_convert_preserves_feedback(self):
        """Test that feedback information is preserved."""
        dataset = [
            {
                "input": "Test",
                "output": "Response",
                "feedback": {"score": 0.75, "type": "rating"},
            },
        ]

        examples = convert_to_dspy_examples(dataset)

        assert len(examples) == 1
        # DSPy Example should preserve feedback field
        assert hasattr(examples[0], "feedback")
        assert examples[0].feedback["score"] == 0.75
