"""Tests for storage security utilities."""

import pytest
from bindu.server.storage.helpers.security import mask_database_url, sanitize_identifier


class TestMaskDatabaseURL:
    """Test database URL masking."""

    def test_mask_postgresql_url(self):
        """Test masking PostgreSQL URL."""
        url = "postgresql+asyncpg://user:password123@localhost:5432/db"  # pragma: allowlist secret
        result = mask_database_url(url)
        assert result == "postgresql+asyncpg://user:***@localhost:5432/db"
        assert "password123" not in result  # pragma: allowlist secret

    def test_mask_mysql_url(self):
        """Test masking MySQL URL."""
        url = "mysql://admin:secret@host:3306/database"  # pragma: allowlist secret
        result = mask_database_url(url)
        assert result == "mysql://admin:***@host:3306/database"
        assert "secret" not in result  # pragma: allowlist secret

    def test_url_without_password(self):
        """Test URL without password."""
        url = "postgresql://localhost:5432/db"
        result = mask_database_url(url)
        assert result == url

    def test_url_without_auth(self):
        """Test URL without authentication."""
        url = "postgresql://localhost/db"
        result = mask_database_url(url)
        assert result == url

    def test_invalid_url_format(self):
        """Test invalid URL format."""
        url = "not-a-valid-url"
        result = mask_database_url(url)
        assert result == url


class TestSanitizeIdentifier:
    """Test SQL identifier sanitization."""

    def test_valid_identifier(self):
        """Test valid SQL identifier."""
        assert sanitize_identifier("table_name") == "table_name"
        assert sanitize_identifier("schema123") == "schema123"
        assert sanitize_identifier("_private") == "_private"

    def test_invalid_identifier_with_dash(self):
        """Test identifier with dash."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            sanitize_identifier("table-name")

    def test_invalid_identifier_with_space(self):
        """Test identifier with space."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            sanitize_identifier("table name")

    def test_invalid_identifier_with_special_chars(self):
        """Test identifier with special characters."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            sanitize_identifier("table;DROP TABLE users--")

    def test_invalid_identifier_with_dot(self):
        """Test identifier with dot."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            sanitize_identifier("schema.table")
