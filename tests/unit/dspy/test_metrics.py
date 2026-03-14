"""Unit tests for bindu.dspy.metrics module.

Tests cover:
- Cosine similarity computation
- Embedding similarity metric
- LLM judge metric
- Metric factory method
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import dspy

from bindu.dspy.metrics import (
    _cosine_similarity,
    embedding_similarity_metric,
    llm_judge_metric,
    get_metric,
)


class TestCosineSimilarity:
    """Test suite for cosine similarity computation."""

    def test_identical_vectors(self):
        """Test cosine similarity of identical vectors."""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])

        similarity = _cosine_similarity(v1, v2)
        assert abs(similarity - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors."""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])

        similarity = _cosine_similarity(v1, v2)
        assert abs(similarity) < 1e-6

    def test_opposite_vectors(self):
        """Test cosine similarity of opposite vectors."""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([-1.0, 0.0, 0.0])

        similarity = _cosine_similarity(v1, v2)
        assert abs(similarity - (-1.0)) < 1e-6

    def test_zero_vector_handling(self):
        """Test that zero vectors return 0.0 similarity."""
        v1 = np.array([0.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])

        similarity = _cosine_similarity(v1, v2)
        assert similarity == 0.0

    def test_both_zero_vectors(self):
        """Test similarity between two zero vectors."""
        v1 = np.array([0.0, 0.0, 0.0])
        v2 = np.array([0.0, 0.0, 0.0])

        similarity = _cosine_similarity(v1, v2)
        assert similarity == 0.0

    def test_normalized_similar_vectors(self):
        """Test similarity of proportional vectors."""
        v1 = np.array([1.0, 1.0, 1.0])
        v2 = np.array([2.0, 2.0, 2.0])

        similarity = _cosine_similarity(v1, v2)
        assert abs(similarity - 1.0) < 1e-6

    def test_similarity_bounds(self):
        """Test that similarity is bounded between -1 and 1."""
        v1 = np.array([1.0, 2.0, 3.0])
        v2 = np.array([4.0, 5.0, 6.0])

        similarity = _cosine_similarity(v1, v2)
        assert -1.0 <= similarity <= 1.0

    def test_multiline_vectors(self):
        """Test cosine similarity with higher dimensional vectors."""
        v1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        v2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        similarity = _cosine_similarity(v1, v2)
        assert abs(similarity - 1.0) < 1e-6


class TestEmbeddingSimilarityMetric:
    """Test suite for embedding similarity metric."""

    def test_metric_returns_callable(self):
        """Test that metric function returns a callable."""
        with patch("bindu.dspy.metrics.dspy.Embedder"):
            metric = embedding_similarity_metric()
            assert callable(metric)

    def test_metric_valid_prediction_dict(self):
        """Test metric with valid prediction dict."""
        with patch("bindu.dspy.metrics.dspy.Embedder") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.return_value = np.array([0.1, 0.2, 0.3])

            metric = embedding_similarity_metric()
            example = dspy.Example(input="test", output="reference output")
            pred = {"output": "generated output"}

            score = metric(example, pred)
            assert 0.0 <= score <= 1.0

    def test_metric_valid_prediction_object(self):
        """Test metric with dspy.Prediction object."""
        with patch("bindu.dspy.metrics.dspy.Embedder") as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder_class.return_value = mock_embedder
            mock_embedder.return_value = np.array([0.1, 0.2, 0.3])

            metric = embedding_similarity_metric()
            example = dspy.Example(input="test", output="reference output")
            pred = MagicMock()
            pred.output = "generated output"

            score = metric(example, pred)
            assert 0.0 <= score <= 1.0

    def test_metric_none_prediction(self):
        """Test metric handles None prediction."""
        with patch("bindu.dspy.metrics.dspy.Embedder") as mock_embedder_class:
            mock_embedder_class.return_value = MagicMock()

            metric = embedding_similarity_metric()
            example = dspy.Example(input="test", output="output")
            score = metric(example, None)
            assert score == 0.0

    def test_metric_empty_output(self):
        """Test metric with empty output."""
        with patch("bindu.dspy.metrics.dspy.Embedder") as mock_embedder_class:
            mock_embedder_class.return_value = MagicMock()

            metric = embedding_similarity_metric()
            example = dspy.Example(input="test", output="")
            pred = {"output": "generated"}
            score = metric(example, pred)
            assert score == 0.0

    def test_metric_exception_handling(self):
        """Test metric handles exceptions."""
        with patch("bindu.dspy.metrics.dspy.Embedder") as mock_embedder_class:
            mock_embedder_class.return_value = MagicMock(side_effect=Exception("Error"))

            metric = embedding_similarity_metric()
            example = dspy.Example(input="test", output="output")
            pred = {"output": "generated"}
            score = metric(example, pred)
            assert score == 0.0


class TestLLMJudgeMetric:
    """Test suite for LLM judge metric."""

    def test_llm_judge_returns_callable(self):
        """Test that LLM judge metric returns callable."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict"):
            metric = llm_judge_metric()
            assert callable(metric)

    def test_llm_judge_valid_prediction(self):
        """Test LLM judge with valid prediction."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict") as mock_predict_class:
            mock_judge = MagicMock()
            mock_predict_class.return_value = mock_judge
            mock_result = MagicMock()
            mock_result.score = "0.85"
            mock_judge.return_value = mock_result

            metric = llm_judge_metric()
            example = dspy.Example(input="test", output="reference")
            pred = {"output": "generated"}

            score = metric(example, pred)
            assert 0.0 <= score <= 1.0

    def test_llm_judge_none_prediction(self):
        """Test LLM judge with None prediction."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict"):
            metric = llm_judge_metric()
            example = dspy.Example(input="test", output="output")
            score = metric(example, None)
            assert score == 0.0

    def test_llm_judge_exception_handling(self):
        """Test LLM judge handles exceptions."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict") as mock_predict_class:
            mock_judge = MagicMock()
            mock_predict_class.return_value = mock_judge
            mock_judge.side_effect = Exception("Judge error")

            metric = llm_judge_metric()
            example = dspy.Example(input="test", output="output")
            pred = {"output": "generated"}
            score = metric(example, pred)
            assert score == 0.0


class TestMetricFactory:
    """Test suite for metric selection factory."""

    def test_get_metric_embedding(self):
        """Test retrieving embedding metric."""
        with patch("bindu.dspy.metrics.dspy.Embedder"):
            metric = get_metric("embedding")
            assert callable(metric)

    def test_get_metric_embedding_case_insensitive(self):
        """Test metric type is case insensitive."""
        with patch("bindu.dspy.metrics.dspy.Embedder"):
            metric1 = get_metric("EMBEDDING")
            metric2 = get_metric("Embedding")
            assert callable(metric1)
            assert callable(metric2)

    def test_get_metric_llm_judge(self):
        """Test retrieving LLM judge metric."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict"):
            metric = get_metric("llm_judge")
            assert callable(metric)

    def test_get_metric_llm_judge_case_insensitive(self):
        """Test LLM judge metric type is case insensitive."""
        with patch("bindu.dspy.metrics.dspy.Signature"), patch("bindu.dspy.metrics.dspy.Predict"):
            metric1 = get_metric("LLM_JUDGE")
            metric2 = get_metric("Llm_Judge")
            assert callable(metric1)
            assert callable(metric2)

    def test_get_metric_invalid_type(self):
        """Test that invalid metric type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown metric type"):
            get_metric("invalid_metric")

    def test_get_metric_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            get_metric("")
