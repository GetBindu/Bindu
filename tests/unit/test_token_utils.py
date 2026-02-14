"""Tests for token utility functions."""

from bindu.utils.agent_token_utils import (
    create_bearer_header,
)


class TestCreateBearerHeader:
    """Test creating bearer header."""

    def test_create_bearer_header(self):
        """Test creating authorization header."""
        header = create_bearer_header("test_token_123")  # pragma: allowlist secret

        assert header == {
            "Authorization": "Bearer test_token_123"
        }  # pragma: allowlist secret

    def test_create_bearer_header_empty(self):
        """Test creating header with empty token."""
        header = create_bearer_header("")
        assert header == {"Authorization": "Bearer "}
