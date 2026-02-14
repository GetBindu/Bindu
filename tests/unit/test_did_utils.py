"""Tests for DID utilities."""

from unittest.mock import MagicMock
from bindu.utils.did_utils import validate_did_extension, check_did_match


class TestValidateDIDExtension:
    """Test DID extension validation."""

    def test_valid_extension(self):
        """Test valid DID extension."""
        mock_ext = MagicMock()
        mock_ext.did = "did:key:test"

        is_valid, error = validate_did_extension(mock_ext, "did")
        assert is_valid is True
        assert error is None

    def test_missing_extension(self):
        """Test missing DID extension."""
        is_valid, error = validate_did_extension(None, "did")
        assert is_valid is False
        assert error == "DID extension not configured"

    def test_missing_attribute(self):
        """Test DID extension missing required attribute."""
        mock_ext = MagicMock()
        del mock_ext.did

        is_valid, error = validate_did_extension(mock_ext, "did")
        assert is_valid is False
        assert error is not None and "missing 'did' attribute" in error

    def test_different_required_attr(self):
        """Test validation with different required attribute."""
        mock_ext = MagicMock()
        mock_ext.get_agent_info = lambda: {}

        is_valid, error = validate_did_extension(mock_ext, "get_agent_info")
        assert is_valid is True
        assert error is None


class TestCheckDIDMatch:
    """Test DID matching."""

    def test_matching_did(self):
        """Test matching DIDs."""
        mock_ext = MagicMock()
        mock_ext.did = "did:key:test123"

        result = check_did_match(mock_ext, "did:key:test123")
        assert result is True

    def test_non_matching_did(self):
        """Test non-matching DIDs."""
        mock_ext = MagicMock()
        mock_ext.did = "did:key:test123"

        result = check_did_match(mock_ext, "did:key:different")
        assert result is False
