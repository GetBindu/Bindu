"""Unit tests for DSPy similarity algorithms."""

import pytest

from bindu.dspy.strategies.similarity import (
    compute_similarity,
    jaccard_similarity,
    overlap_similarity,
    tokenize,
    weighted_similarity,
)


class TestTokenize:
    """Test tokenize function."""

    def test_tokenize_basic(self):
        """Test simple string is tokenized."""
        result = tokenize("Hello world")
        assert result == ["hello", "world"]

    def test_tokenize_lowercases(self):
        """Test uppercase is converted to lowercase."""
        result = tokenize("HELLO World")
        assert result == ["hello", "world"]

    def test_tokenize_splits_on_whitespace(self):
        """Test splits on spaces, tabs, newlines."""
        result = tokenize("hello\tworld\nnew line")
        assert "hello" in result
        assert "world" in result
        assert "new" in result
        assert "line" in result

    def test_tokenize_empty_string(self):
        """Test empty string returns empty list."""
        result = tokenize("")
        assert result == []

    def test_tokenize_preserves_punctuation(self):
        """Test punctuation is attached to words."""
        result = tokenize("Hello, world!")
        assert "hello," in result
        assert "world!" in result


class TestJaccardSimilarity:
    """Test jaccard_similarity function."""

    def test_jaccard_identical_texts(self):
        """Test identical texts return 1.0."""
        text = "the quick brown fox"
        result = jaccard_similarity(text, text)
        assert result == 1.0

    def test_jaccard_no_overlap(self):
        """Test no common words return 0.0."""
        result = jaccard_similarity("hello world", "goodbye universe")
        assert result == 0.0

    def test_jaccard_partial_overlap(self):
        """Test partial overlap returns fraction."""
        text1 = "the quick brown fox"
        text2 = "the lazy brown dog"
        result = jaccard_similarity(text1, text2)
        
        # Intersection: {the, brown} = 2
        # Union: {the, quick, brown, fox, lazy, dog} = 6
        # Jaccard = 2/6 = 0.333...
        assert 0.3 < result < 0.4

    def test_jaccard_different_case(self):
        """Test case-insensitive comparison."""
        result = jaccard_similarity("HELLO WORLD", "hello world")
        assert result == 1.0

    def test_jaccard_empty_text(self):
        """Test empty text returns 0.0."""
        result = jaccard_similarity("", "hello world")
        assert result == 0.0

    def test_jaccard_one_empty(self):
        """Test one empty text returns 0.0."""
        result = jaccard_similarity("hello", "")
        assert result == 0.0

    def test_jaccard_example_calculation(self):
        """Test known example is verified."""
        # "a b c" vs "b c d"
        # Intersection: {b, c} = 2
        # Union: {a, b, c, d} = 4
        # Jaccard = 2/4 = 0.5
        result = jaccard_similarity("a b c", "b c d")
        assert result == 0.5


class TestOverlapSimilarity:
    """Test overlap_similarity function."""

    def test_overlap_identical_texts(self):
        """Test identical texts return 1.0."""
        text = "hello world"
        result = overlap_similarity(text, text)
        assert result == 1.0

    def test_overlap_no_overlap(self):
        """Test no overlap returns 0.0."""
        result = overlap_similarity("hello world", "goodbye universe")
        assert result == 0.0

    def test_overlap_subset(self):
        """Test complete subset returns 1.0."""
        result = overlap_similarity("hello", "hello world today")
        assert result == 1.0

    def test_overlap_partial_overlap(self):
        """Test partial overlap is calculated correctly."""
        # "a b c" vs "b c d e"
        # Intersection: {b, c} = 2
        # Min size: min(3, 4) = 3
        # Overlap = 2/3 = 0.666...
        result = overlap_similarity("a b c", "b c d e")
        assert 0.6 < result < 0.7

    def test_overlap_different_lengths(self):
        """Test shorter text determines denominator."""
        result = overlap_similarity("a b", "a b c d e f")
        # Intersection: {a, b} = 2
        # Min size: min(2, 6) = 2
        # Overlap = 2/2 = 1.0
        assert result == 1.0

    def test_overlap_empty_text(self):
        """Test empty text returns 0.0."""
        result = overlap_similarity("", "hello")
        assert result == 0.0


class TestWeightedSimilarity:
    """Test weighted_similarity function."""

    def test_weighted_identical_texts(self):
        """Test identical returns high score."""
        text = "hello world"
        result = weighted_similarity(text, text)
        assert result > 0.9  # Should be very high

    def test_weighted_no_overlap(self):
        """Test no overlap returns 0.0."""
        result = weighted_similarity("hello world", "goodbye universe")
        assert result == 0.0

    def test_weighted_rare_terms_higher_weight(self):
        """Test rare words are weighted more."""
        corpus = [
            "common word appears everywhere",
            "common word is here too",
            "common word again",
            "rare_term appears once",
        ]
        
        # Text with rare term should have higher weight
        text1 = "rare_term here"
        text2 = "common word"
        
        # When comparing against another text with rare_term
        score_rare = weighted_similarity(text1, "rare_term test", corpus=corpus)
        # When comparing common words
        score_common = weighted_similarity(text2, "common test", corpus=corpus)
        
        # Rare terms should get higher weight
        assert score_rare > 0

    def test_weighted_common_terms_lower_weight(self):
        """Test common words are weighted less."""
        corpus = [
            "the the the the",
            "the is common",
            "the word here",
        ]
        
        # Common word should have lower weight
        result = weighted_similarity("the", "the the", corpus=corpus)
        assert result > 0  # Still some similarity

    def test_weighted_with_custom_corpus(self):
        """Test custom corpus is used for IDF."""
        corpus = ["doc1 text", "doc2 text", "doc3 unique"]
        result = weighted_similarity("text test", "text here", corpus=corpus)
        assert result > 0

    def test_weighted_without_corpus(self):
        """Test defaults to using both texts."""
        result = weighted_similarity("hello world", "world hello")
        assert result > 0.9  # Should be very similar

    def test_weighted_empty_text(self):
        """Test empty text returns 0.0."""
        result = weighted_similarity("", "hello")
        assert result == 0.0

    def test_weighted_normalization(self):
        """Test scores are normalized to [0, 1]."""
        result = weighted_similarity("hello world", "hello there")
        assert 0.0 <= result <= 1.0


class TestComputeSimilarity:
    """Test compute_similarity dispatcher function."""

    def test_compute_jaccard_method(self):
        """Test calls jaccard_similarity."""
        result = compute_similarity("hello world", "hello world", method="jaccard")
        assert result == 1.0

    def test_compute_weighted_method(self):
        """Test calls weighted_similarity."""
        result = compute_similarity("hello", "hello", method="weighted")
        assert result > 0.9

    def test_compute_overlap_method(self):
        """Test calls overlap_similarity."""
        result = compute_similarity("hello", "hello world", method="overlap")
        assert result == 1.0

    def test_compute_invalid_method_raises(self):
        """Test invalid method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown similarity method"):
            compute_similarity("text1", "text2", method="invalid")

    def test_compute_passes_corpus(self):
        """Test corpus is passed to weighted method."""
        corpus = ["doc1", "doc2"]
        result = compute_similarity(
            "test", "test",
            method="weighted",
            corpus=corpus
        )
        assert result > 0
