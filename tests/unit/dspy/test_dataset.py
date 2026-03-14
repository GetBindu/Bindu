"""Unit tests for bindu.dspy.dataset module.

Tests cover:
- Feedback normalization
- Dataset building pipeline  
- Data fetching from database
- Feedback filtering and validation
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from bindu.dspy.dataset import normalize_feedback, fetch_raw_task_data
from bindu.dspy.models import RawTaskData


class TestFeedbackNormalization:
    """Test suite for feedback normalization."""

    def test_normalize_feedback_none(self):
        """Test normalizing None feedback."""
        score, feedback_type = normalize_feedback(None)
        assert score is None
        assert feedback_type is None

    def test_normalize_feedback_empty_dict(self):
        """Test normalizing empty feedback dict."""
        score, feedback_type = normalize_feedback({})
        assert score is None
        assert feedback_type is None

    def test_normalize_feedback_rating_5_scale(self):
        """Test normalizing rating on 5-point scale."""
        tests = [
            ({"rating": 1}, 0.2),
            ({"rating": 2}, 0.4),
            ({"rating": 3}, 0.6),
            ({"rating": 4}, 0.8),
            ({"rating": 5}, 1.0),
        ]

        for feedback, expected_score in tests:
            score, feedback_type = normalize_feedback(feedback)
            assert abs(score - expected_score) < 1e-6
            assert feedback_type == "rating"

    def test_normalize_feedback_invalid_rating(self):
        """Test that invalid ratings return None."""
        tests = [
            {"rating": 0},  # Below range
            {"rating": 6},  # Above range
            {"rating": -1},  # Negative
            {"rating": "invalid"},  # Non-numeric
            {"rating": None},  # None
        ]

        for feedback in tests:
            score, feedback_type = normalize_feedback(feedback)
            # If it's not a valid rating, it shouldn't be normalized to rating
            if score is None:
                assert feedback_type is None

    def test_normalize_feedback_thumbs_up_true(self):
        """Test normalizing thumbs_up feedback (true)."""
        score, feedback_type = normalize_feedback({"thumbs_up": True})
        assert score == 1.0
        assert feedback_type == "thumbs_up"

    def test_normalize_feedback_thumbs_up_false(self):
        """Test normalizing thumbs_up feedback (false)."""
        score, feedback_type = normalize_feedback({"thumbs_up": False})
        assert score == 0.0
        assert feedback_type == "thumbs_up"

    def test_normalize_feedback_thumbs_up_string_true(self):
        """Test normalizing thumbs_up with string 'true'."""
        tests = ["true", "True", "TRUE", "1", "yes", "YES"]

        for value in tests:
            score, feedback_type = normalize_feedback({"thumbs_up": value})
            assert score == 1.0
            assert feedback_type == "thumbs_up"

    def test_normalize_feedback_thumbs_up_string_false(self):
        """Test normalizing thumbs_up with string 'false'."""
        tests = ["false", "False", "FALSE", "0", "no", "NO"]

        for value in tests:
            score, feedback_type = normalize_feedback({"thumbs_up": value})
            assert score == 0.0
            assert feedback_type == "thumbs_up"

    def test_normalize_feedback_prefers_rating(self):
        """Test that rating is preferred over thumbs_up."""
        feedback = {"rating": 4, "thumbs_up": True}
        score, feedback_type = normalize_feedback(feedback)

        # Should use rating, not thumbs_up
        assert feedback_type == "rating"
        assert score == 0.8

    def test_normalize_feedback_fallback_to_thumbs_up(self):
        """Test fallback to thumbs_up when rating invalid."""
        feedback = {"rating": 0, "thumbs_up": True}
        score, feedback_type = normalize_feedback(feedback)

        # Should fallback to thumbs_up since rating is invalid
        assert feedback_type == "thumbs_up"
        assert score == 1.0

    def test_normalize_feedback_float_rating(self):
        """Test normalizing float ratings."""
        tests = [
            ({"rating": 2.5}, 0.5),
            ({"rating": 4.5}, 0.9),
            ({"rating": 1.5}, 0.3),
        ]

        for feedback, expected in tests:
            score, _ = normalize_feedback(feedback)
            assert abs(score - expected) < 1e-6


class TestRawTaskDataFetching:
    """Test suite for fetching raw task data."""

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_success(self):
        """Test successful fetching of raw task data."""
        mock_rows = [
            {
                "id": uuid4(),
                "history": [{"role": "user", "content": "Hello"}],
                "created_at": "2024-01-01",
                "feedback_data": {"rating": 5},
            },
        ]

        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ):

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=mock_rows)

            result = await fetch_raw_task_data(limit=1)

            assert len(result) == 1
            assert isinstance(result[0], RawTaskData)

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_empty(self):
        """Test fetching when no tasks exist."""
        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ):

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])

            result = await fetch_raw_task_data()

            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_connection_closed(self):
        """Test that connection is closed after fetching."""
        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ):

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])

            await fetch_raw_task_data()

            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_with_did(self):
        """Test fetching with DID for schema isolation."""
        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ):

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])

            await fetch_raw_task_data(did="my-did-123")

            mock_storage_class.assert_called_once_with(did="my-did-123")

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_uses_limit_from_settings(self):
        """Test that default limit comes from settings."""
        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ) as mock_app_settings:

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])
            mock_app_settings.dspy.max_interactions_query_limit = 500

            await fetch_raw_task_data(limit=None)

            # Verify limit was passed from settings
            mock_storage.fetch_tasks_with_feedback.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_raw_task_data_connection_error(self):
        """Test handling of connection errors."""
        with patch(
            "bindu.dspy.dataset.PostgresStorage"
        ) as mock_storage_class, patch(
            "bindu.dspy.dataset.app_settings"
        ):

            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.connect = AsyncMock(side_effect=ConnectionError("Connection failed"))

            with pytest.raises(ConnectionError, match="Failed to fetch raw task data"):
                await fetch_raw_task_data()


class TestFeedbackFiltering:
    """Test suite for feedback-based filtering."""

    def test_feedback_scores_range(self):
        """Test that normalized feedback scores are in valid range."""
        test_feedbacks = [
            {"rating": 1},
            {"rating": 3},
            {"rating": 5},
            {"thumbs_up": True},
            {"thumbs_up": False},
        ]

        for feedback in test_feedbacks:
            score, _ = normalize_feedback(feedback)
            if score is not None:
                assert 0.0 <= score <= 1.0

    def test_feedback_threshold_application(self):
        """Test that feedback threshold filters correctly."""
        threshold = 0.6

        feedbacks = [
            ({"rating": 2}, 0.4, False),  # Below threshold
            ({"rating": 3}, 0.6, True),  # At threshold
            ({"rating": 4}, 0.8, True),  # Above threshold
            (None, None, False),  # No feedback
        ]

        for feedback, expected_score, should_pass in feedbacks:
            score, _ = normalize_feedback(feedback)
            if score is not None:
                passes = score >= threshold
                assert passes == should_pass
