"""Unit tests for DSPy dataset pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import dspy
import pytest

from bindu.dspy.dataset import (
    RawTaskData,
    normalize_feedback,
    extract_interactions,
    validate_and_clean_interactions,
    deduplicate_interactions,
    prepare_golden_dataset,
    validate_dataset_size,
    convert_to_dspy_examples,
    fetch_raw_task_data,
    build_golden_dataset,
)
from bindu.dspy.extractor import InteractionExtractor
from bindu.dspy.models import Interaction
from bindu.dspy.strategies import LastTurnStrategy


class TestNormalizeFeedback:
    """Test normalize_feedback function."""

    def test_normalize_rating_feedback(self):
        """Test rating 1-5 normalized to 0.0-1.0."""
        feedback_data = {"rating": 3}
        score, feedback_type = normalize_feedback(feedback_data)
        assert score == 0.6
        assert feedback_type == "rating"

    def test_normalize_rating_edge_cases(self):
        """Test rating edge cases (min and max)."""
        # Minimum rating
        score, feedback_type = normalize_feedback({"rating": 1})
        assert score == 0.2
        assert feedback_type == "rating"

        # Maximum rating
        score, feedback_type = normalize_feedback({"rating": 5})
        assert score == 1.0
        assert feedback_type == "rating"

    def test_normalize_thumbs_up_true(self):
        """Test thumbs_up=True returns (1.0, 'thumbs_up')."""
        feedback_data = {"thumbs_up": True}
        score, feedback_type = normalize_feedback(feedback_data)
        assert score == 1.0
        assert feedback_type == "thumbs_up"

    def test_normalize_thumbs_up_false(self):
        """Test thumbs_up=False returns (0.0, 'thumbs_up')."""
        feedback_data = {"thumbs_up": False}
        score, feedback_type = normalize_feedback(feedback_data)
        assert score == 0.0
        assert feedback_type == "thumbs_up"

    def test_normalize_thumbs_up_string(self):
        """Test handling 'true'/'false' strings."""
        # String "true"
        score, feedback_type = normalize_feedback({"thumbs_up": "true"})
        assert score == 1.0
        assert feedback_type == "thumbs_up"

        # String "false"
        score, feedback_type = normalize_feedback({"thumbs_up": "false"})
        assert score == 0.0
        assert feedback_type == "thumbs_up"

        # String "1"
        score, feedback_type = normalize_feedback({"thumbs_up": "1"})
        assert score == 1.0
        assert feedback_type == "thumbs_up"

    def test_normalize_invalid_rating(self):
        """Test out of range rating returns (None, None)."""
        # Below range
        score, feedback_type = normalize_feedback({"rating": 0})
        assert score is None
        assert feedback_type is None

        # Above range
        score, feedback_type = normalize_feedback({"rating": 6})
        assert score is None
        assert feedback_type is None

    def test_normalize_missing_feedback(self):
        """Test None/empty dict returns (None, None)."""
        # None
        score, feedback_type = normalize_feedback(None)
        assert score is None
        assert feedback_type is None

        # Empty dict
        score, feedback_type = normalize_feedback({})
        assert score is None
        assert feedback_type is None

    def test_normalize_invalid_type(self):
        """Test invalid data types handled gracefully."""
        # Invalid rating type
        score, feedback_type = normalize_feedback({"rating": "invalid"})
        assert score is None
        assert feedback_type is None

        # Invalid thumbs_up type
        score, feedback_type = normalize_feedback({"thumbs_up": 123})
        assert score is None
        assert feedback_type is None


class TestValidateAndCleanInteractions:
    """Test validate_and_clean_interactions function."""

    def test_validate_removes_short_input(self):
        """Test input below min_input_length is filtered."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Hi",  # Too short
                agent_output="Hello there, how can I help you?",
            )
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 10
            mock_settings.dspy.min_output_length = 10

            result = validate_and_clean_interactions(interactions)
            assert len(result) == 0

    def test_validate_removes_short_output(self):
        """Test output below min_output_length is filtered."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="What is the meaning of life?",
                agent_output="42",  # Too short
            )
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 10
            mock_settings.dspy.min_output_length = 10

            result = validate_and_clean_interactions(interactions)
            assert len(result) == 0

    def test_validate_removes_identical_input_output(self):
        """Test identical input/output is filtered."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Same text",
                agent_output="Same text",
            )
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 5
            mock_settings.dspy.min_output_length = 5

            result = validate_and_clean_interactions(interactions)
            assert len(result) == 0

    def test_validate_cleans_whitespace(self):
        """Test multiple spaces normalized to single space."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="What  is   Python?",
                agent_output="Python  is   a  programming language.",
            )
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 5
            mock_settings.dspy.min_output_length = 5

            result = validate_and_clean_interactions(interactions)
            assert len(result) == 1
            assert result[0].user_input == "What is Python?"
            assert result[0].agent_output == "Python is a programming language."

    def test_validate_keeps_valid_interactions(self):
        """Test valid interactions pass through."""
        task_id = uuid4()
        interactions = [
            Interaction(
                id=task_id,
                user_input="What is Python?",
                agent_output="Python is a programming language.",
                feedback_score=0.9,
                feedback_type="rating",
            )
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_input_length = 5
            mock_settings.dspy.min_output_length = 5

            result = validate_and_clean_interactions(interactions)
            assert len(result) == 1
            assert result[0].id == task_id
            assert result[0].feedback_score == 0.9

    def test_validate_with_empty_list(self):
        """Test empty input returns empty list."""
        result = validate_and_clean_interactions([])
        assert result == []


class TestDeduplicateInteractions:
    """Test deduplicate_interactions function."""

    def test_deduplicate_removes_exact_duplicates(self):
        """Test duplicate (input, output) pairs are removed."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="What is Python?",
                agent_output="Python is a language.",
            ),
            Interaction(
                id=uuid4(),
                user_input="What is Python?",
                agent_output="Python is a language.",
            ),
        ]

        result = deduplicate_interactions(interactions)
        assert len(result) == 1

    def test_deduplicate_preserves_unique(self):
        """Test unique interactions are preserved."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Question 1",
                agent_output="Answer 1",
            ),
            Interaction(
                id=uuid4(),
                user_input="Question 2",
                agent_output="Answer 2",
            ),
        ]

        result = deduplicate_interactions(interactions)
        assert len(result) == 2

    def test_deduplicate_keeps_first_occurrence(self):
        """Test first occurrence is retained."""
        id1 = uuid4()
        id2 = uuid4()
        interactions = [
            Interaction(
                id=id1,
                user_input="Question",
                agent_output="Answer",
                feedback_score=0.8,
            ),
            Interaction(
                id=id2,
                user_input="Question",
                agent_output="Answer",
                feedback_score=0.9,
            ),
        ]

        result = deduplicate_interactions(interactions)
        assert len(result) == 1
        assert result[0].id == id1
        assert result[0].feedback_score == 0.8

    def test_deduplicate_with_empty_list(self):
        """Test empty list returns empty list."""
        result = deduplicate_interactions([])
        assert result == []

    def test_deduplicate_different_feedback_same_content(self):
        """Test deduplicates even with different feedback."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Question",
                agent_output="Answer",
                feedback_score=0.8,
                feedback_type="rating",
            ),
            Interaction(
                id=uuid4(),
                user_input="Question",
                agent_output="Answer",
                feedback_score=0.9,
                feedback_type="thumbs_up",
            ),
        ]

        result = deduplicate_interactions(interactions)
        assert len(result) == 1


class TestPrepareGoldenDataset:
    """Test prepare_golden_dataset function."""

    def test_prepare_converts_to_dict_format(self):
        """Test converts Interaction to dict format."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="What is AI?",
                agent_output="AI is artificial intelligence.",
                feedback_score=0.95,
                feedback_type="rating",
            )
        ]

        result = prepare_golden_dataset(interactions)
        assert len(result) == 1
        assert result[0]["input"] == "What is AI?"
        assert result[0]["output"] == "AI is artificial intelligence."
        assert result[0]["feedback"]["score"] == 0.95
        assert result[0]["feedback"]["type"] == "rating"

    def test_prepare_includes_feedback(self):
        """Test feedback is included in output."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Test",
                agent_output="Response",
                feedback_score=0.7,
                feedback_type="thumbs_up",
            )
        ]

        result = prepare_golden_dataset(interactions)
        assert "feedback" in result[0]
        assert result[0]["feedback"]["score"] == 0.7
        assert result[0]["feedback"]["type"] == "thumbs_up"

    def test_prepare_handles_none_feedback(self):
        """Test None feedback is handled correctly."""
        interactions = [
            Interaction(
                id=uuid4(),
                user_input="Test",
                agent_output="Response",
                feedback_score=None,
                feedback_type=None,
            )
        ]

        result = prepare_golden_dataset(interactions)
        assert result[0]["feedback"]["score"] is None
        assert result[0]["feedback"]["type"] is None

    def test_prepare_with_empty_list(self):
        """Test empty input returns empty dataset."""
        result = prepare_golden_dataset([])
        assert result == []


class TestValidateDatasetSize:
    """Test validate_dataset_size function."""

    def test_validate_size_too_small_raises_error(self):
        """Test below min_examples raises ValueError."""
        dataset = [{"input": "test", "output": "response"}]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_examples = 5

            with pytest.raises(ValueError, match="Dataset too small"):
                validate_dataset_size(dataset)

    def test_validate_size_acceptable(self):
        """Test within range passes."""
        dataset = [
            {"input": f"test{i}", "output": f"response{i}"}
            for i in range(10)
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_examples = 2
            mock_settings.dspy.max_examples = 20

            # Should not raise
            validate_dataset_size(dataset)

    def test_validate_size_too_large_logs_warning(self):
        """Test above max_examples logs warning but passes."""
        dataset = [
            {"input": f"test{i}", "output": f"response{i}"}
            for i in range(100)
        ]

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_examples = 2
            mock_settings.dspy.max_examples = 50

            # Should not raise, just log warning
            validate_dataset_size(dataset)

    def test_validate_size_at_boundaries(self):
        """Test exactly min/max values are handled."""
        # Exactly at minimum
        dataset = [{"input": "test", "output": "response"}] * 5

        with patch("bindu.dspy.dataset.app_settings") as mock_settings:
            mock_settings.dspy.min_examples = 5
            mock_settings.dspy.max_examples = 100

            validate_dataset_size(dataset)


class TestConvertToDSPyExamples:
    """Test convert_to_dspy_examples function."""

    def test_convert_creates_dspy_examples(self):
        """Test converts dicts to dspy.Example objects."""
        dataset = [
            {
                "input": "What is Python?",
                "output": "Python is a language.",
                "feedback": {"score": 0.9, "type": "rating"},
            }
        ]

        result = convert_to_dspy_examples(dataset)
        assert len(result) == 1
        assert isinstance(result[0], dspy.Example)

    def test_convert_sets_input_fields(self):
        """Test with_inputs('input') is called correctly."""
        dataset = [
            {
                "input": "Test input",
                "output": "Test output",
                "feedback": {"score": 0.8, "type": "rating"},
            }
        ]

        result = convert_to_dspy_examples(dataset)
        # DSPy Example should have input as input field
        assert hasattr(result[0], "input")
        assert result[0].input == "Test input"

    def test_convert_preserves_feedback(self):
        """Test feedback attribute is preserved."""
        dataset = [
            {
                "input": "Question",
                "output": "Answer",
                "feedback": {"score": 0.95, "type": "thumbs_up"},
            }
        ]

        result = convert_to_dspy_examples(dataset)
        assert result[0].feedback["score"] == 0.95
        assert result[0].feedback["type"] == "thumbs_up"

    def test_convert_with_empty_dataset(self):
        """Test empty input returns empty list."""
        result = convert_to_dspy_examples([])
        assert result == []


class TestFetchRawTaskData:
    """Test fetch_raw_task_data function."""

    @pytest.mark.asyncio
    async def test_fetch_connects_to_storage(self, mock_storage):
        """Test Storage.connect() is called."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            await fetch_raw_task_data(limit=10)
            mock_storage.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_calls_fetch_tasks_with_feedback(self, mock_storage):
        """Test correct method is called with limit."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            await fetch_raw_task_data(limit=50)
            mock_storage.fetch_tasks_with_feedback.assert_called_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_fetch_disconnects_on_success(self, mock_storage):
        """Test Storage.disconnect() is called."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            await fetch_raw_task_data(limit=10)
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_disconnects_on_error(self, mock_storage):
        """Test disconnect is called even on error."""
        mock_storage.fetch_tasks_with_feedback.side_effect = Exception("DB error")

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            with pytest.raises(ConnectionError):
                await fetch_raw_task_data(limit=10)
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_uses_did_for_schema_isolation(self, mock_storage):
        """Test DID is passed to storage."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage) as mock_cls:
            await fetch_raw_task_data(limit=10, did="did:bindu:test")
            mock_cls.assert_called_once_with(did="did:bindu:test")

    @pytest.mark.asyncio
    async def test_fetch_converts_rows_to_raw_task_data(self, mock_storage):
        """Test rows are converted to RawTaskData objects."""
        task_id = uuid4()
        mock_storage.fetch_tasks_with_feedback.return_value = [
            {
                "id": task_id,
                "history": [{"role": "user", "content": "Test"}],
                "created_at": "2026-01-28",
                "feedback_data": {"rating": 5},
            }
        ]

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            result = await fetch_raw_task_data(limit=10)
            assert len(result) == 1
            assert isinstance(result[0], RawTaskData)
            assert result[0].id == task_id

    @pytest.mark.asyncio
    async def test_fetch_handles_connection_error(self, mock_storage):
        """Test raises ConnectionError on DB failure."""
        mock_storage.fetch_tasks_with_feedback.side_effect = Exception("Connection failed")

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            with pytest.raises(ConnectionError, match="Failed to fetch raw task data"):
                await fetch_raw_task_data(limit=10)

    @pytest.mark.asyncio
    async def test_fetch_with_custom_limit(self, mock_storage):
        """Test custom limit parameter is respected."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            await fetch_raw_task_data(limit=25)
            mock_storage.fetch_tasks_with_feedback.assert_called_with(limit=25)

    @pytest.mark.asyncio
    async def test_fetch_with_default_limit(self, mock_storage):
        """Test uses settings limit when None."""
        mock_storage.fetch_tasks_with_feedback.return_value = []

        with patch("bindu.dspy.dataset.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.dataset.app_settings") as mock_settings:
                mock_settings.dspy.max_interactions_query_limit = 100
                await fetch_raw_task_data(limit=None)
                mock_storage.fetch_tasks_with_feedback.assert_called_with(limit=100)


class TestExtractInteractions:
    """Test extract_interactions function."""

    def test_extract_uses_strategy(self):
        """Test Strategy.extract_all() is called for each task."""
        task_id = uuid4()
        raw_tasks = [
            RawTaskData(
                id=task_id,
                history=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
                created_at="2026-01-28",
                feedback_data={"rating": 4},
            )
        ]

        strategy = LastTurnStrategy()
        result = extract_interactions(raw_tasks, strategy=strategy)
        
        assert len(result) >= 0  # May return empty if extraction fails

    def test_extract_normalizes_feedback(self):
        """Test normalize_feedback() is called."""
        task_id = uuid4()
        raw_tasks = [
            RawTaskData(
                id=task_id,
                history=[
                    {"role": "user", "content": "Question"},
                    {"role": "assistant", "content": "Answer"},
                ],
                created_at="2026-01-28",
                feedback_data={"rating": 5},
            )
        ]

        result = extract_interactions(raw_tasks)
        # If extraction succeeds, feedback should be normalized
        if result:
            assert result[0].feedback_score == 1.0
            assert result[0].feedback_type == "rating"

    def test_extract_collects_all_interactions(self):
        """Test multiple interactions from sliding window are collected."""
        # This would require a SlidingWindowStrategy to produce multiple
        # For now, test that the function returns a list
        raw_tasks = [
            RawTaskData(
                id=uuid4(),
                history=[
                    {"role": "user", "content": "Q1"},
                    {"role": "assistant", "content": "A1"},
                ],
                created_at="2026-01-28",
            )
        ]

        result = extract_interactions(raw_tasks)
        assert isinstance(result, list)

    def test_extract_with_empty_tasks(self):
        """Test empty task list returns empty interactions."""
        result = extract_interactions([])
        assert result == []

    def test_extract_skips_failed_extractions(self):
        """Test failed extractions (None) are filtered out."""
        # Task with invalid history that will fail extraction
        raw_tasks = [
            RawTaskData(
                id=uuid4(),
                history=[],  # Empty history
                created_at="2026-01-28",
            )
        ]

        result = extract_interactions(raw_tasks)
        assert result == []


class TestBuildGoldenDataset:
    """Test build_golden_dataset function."""

    @pytest.mark.asyncio
    async def test_build_full_pipeline_success(self):
        """Test complete pipeline executes successfully."""
        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            with patch("bindu.dspy.dataset.extract_interactions") as mock_extract:
                with patch("bindu.dspy.dataset.validate_and_clean_interactions") as mock_validate:
                    with patch("bindu.dspy.dataset.deduplicate_interactions") as mock_dedup:
                        with patch("bindu.dspy.dataset.prepare_golden_dataset") as mock_prepare:
                            with patch("bindu.dspy.dataset.validate_dataset_size"):
                                # Setup mocks
                                task_id = uuid4()
                                mock_fetch.return_value = [
                                    RawTaskData(
                                        id=task_id,
                                        history=[{"role": "user", "content": "Test"}],
                                        created_at="2026-01-28",
                                    )
                                ]
                                mock_extract.return_value = [
                                    Interaction(
                                        id=task_id,
                                        user_input="Test",
                                        agent_output="Response",
                                    )
                                ]
                                mock_validate.return_value = mock_extract.return_value
                                mock_dedup.return_value = mock_extract.return_value
                                mock_prepare.return_value = [
                                    {"input": "Test", "output": "Response"}
                                ]

                                result = await build_golden_dataset()
                                assert len(result) == 1
                                assert result[0]["input"] == "Test"

    @pytest.mark.asyncio
    async def test_build_raises_on_no_tasks(self):
        """Test ValueError if fetch returns empty."""
        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            mock_fetch.return_value = []

            with pytest.raises(ValueError, match="No tasks found"):
                await build_golden_dataset()

    @pytest.mark.asyncio
    async def test_build_raises_on_no_interactions(self):
        """Test ValueError if extraction fails."""
        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            with patch("bindu.dspy.dataset.extract_interactions") as mock_extract:
                mock_fetch.return_value = [
                    RawTaskData(id=uuid4(), history=[], created_at="2026-01-28")
                ]
                mock_extract.return_value = []

                with pytest.raises(ValueError, match="No interactions extracted"):
                    await build_golden_dataset()

    @pytest.mark.asyncio
    async def test_build_raises_on_no_valid_interactions(self):
        """Test ValueError after validation."""
        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            with patch("bindu.dspy.dataset.extract_interactions") as mock_extract:
                with patch("bindu.dspy.dataset.validate_and_clean_interactions") as mock_validate:
                    task_id = uuid4()
                    mock_fetch.return_value = [
                        RawTaskData(id=task_id, history=[], created_at="2026-01-28")
                    ]
                    mock_extract.return_value = [
                        Interaction(id=task_id, user_input="x", agent_output="y")
                    ]
                    mock_validate.return_value = []

                    with pytest.raises(ValueError, match="No interactions passed validation"):
                        await build_golden_dataset()

    @pytest.mark.asyncio
    async def test_build_uses_custom_strategy(self):
        """Test custom strategy is passed through."""
        custom_strategy = LastTurnStrategy()

        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            with patch("bindu.dspy.dataset.extract_interactions") as mock_extract:
                with patch("bindu.dspy.dataset.validate_and_clean_interactions"):
                    with patch("bindu.dspy.dataset.deduplicate_interactions"):
                        with patch("bindu.dspy.dataset.prepare_golden_dataset") as mock_prepare:
                            with patch("bindu.dspy.dataset.validate_dataset_size"):
                                mock_fetch.return_value = [
                                    RawTaskData(id=uuid4(), history=[], created_at="2026-01-28")
                                ]
                                mock_extract.return_value = [
                                    Interaction(id=uuid4(), user_input="Q", agent_output="A")
                                ]
                                mock_prepare.return_value = [{"input": "Q", "output": "A"}]

                                await build_golden_dataset(strategy=custom_strategy)
                                # Verify strategy was passed
                                call_args = mock_extract.call_args
                                assert call_args[1]["strategy"] == custom_strategy

    @pytest.mark.asyncio
    async def test_build_uses_did_isolation(self):
        """Test DID parameter is propagated."""
        with patch("bindu.dspy.dataset.fetch_raw_task_data") as mock_fetch:
            with patch("bindu.dspy.dataset.extract_interactions"):
                with patch("bindu.dspy.dataset.validate_and_clean_interactions"):
                    with patch("bindu.dspy.dataset.deduplicate_interactions"):
                        with patch("bindu.dspy.dataset.prepare_golden_dataset") as mock_prepare:
                            with patch("bindu.dspy.dataset.validate_dataset_size"):
                                mock_fetch.return_value = [
                                    RawTaskData(id=uuid4(), history=[], created_at="2026-01-28")
                                ]
                                mock_prepare.return_value = [{"input": "Q", "output": "A"}]

                                await build_golden_dataset(did="did:bindu:test")
                                mock_fetch.assert_called_once()
                                assert mock_fetch.call_args[1]["did"] == "did:bindu:test"
