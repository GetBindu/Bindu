"""Minimal tests for capability calculator."""

import pytest

from bindu.server.negotiation.capability_calculator import (
    ScoringWeights,
    SkillMatchResult,
    AssessmentResult,
)


class TestScoringWeights:
    """Test scoring weights functionality."""

    def test_default_weights_initialization(self):
        """Test that default weights can be initialized."""
        weights = ScoringWeights()

        assert weights.skill_match >= 0
        assert weights.io_compatibility >= 0
        assert weights.performance >= 0
        assert weights.load >= 0
        assert weights.cost >= 0

    def test_normalized_weights_sum_to_one(self):
        """Test that normalized weights sum to 1.0."""
        weights = ScoringWeights(
            skill_match=0.3, io_compatibility=0.2, performance=0.2, load=0.2, cost=0.1
        )

        normalized = weights.normalized
        total = sum(normalized.values())

        assert abs(total - 1.0) < 1e-10

    def test_negative_weight_raises_error(self):
        """Test that negative weights raise ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            ScoringWeights(skill_match=-0.1)

    def test_zero_weights_use_equal_distribution(self):
        """Test that all zero weights result in equal distribution."""
        weights = ScoringWeights(
            skill_match=0.0, io_compatibility=0.0, performance=0.0, load=0.0, cost=0.0
        )

        normalized = weights.normalized

        assert all(v == 0.2 for v in normalized.values())

    def test_normalized_property_is_cached(self):
        """Test that normalized property is cached."""
        weights = ScoringWeights()

        # Access twice should return same object
        first = weights.normalized
        second = weights.normalized

        assert first is second


class TestSkillMatchResult:
    """Test skill match result dataclass."""

    def test_skill_match_result_creation(self):
        """Test creating skill match result."""
        result = SkillMatchResult(
            skill_id="skill-123", skill_name="Data Analysis", score=0.85
        )

        assert result.skill_id == "skill-123"
        assert result.skill_name == "Data Analysis"
        assert result.score == 0.85


class TestAssessmentResult:
    """Test assessment result dataclass."""

    def test_assessment_result_creation(self):
        """Test creating assessment result."""
        result = AssessmentResult(accepted=True, score=0.75, confidence=0.8)

        assert result.accepted is True
        assert result.score == 0.75
        assert result.confidence == 0.8
        assert isinstance(result.skill_matches, list)

    def test_assessment_result_with_rejection(self):
        """Test assessment result with rejection."""
        result = AssessmentResult(
            accepted=False,
            score=0.2,
            confidence=0.6,
            rejection_reason="Insufficient skill match",
        )

        assert result.accepted is False
        assert result.rejection_reason == "Insufficient skill match"
