"""Tests for security utilities."""

import pytest
from bindu.utils.security import validate_password_strength


class TestValidatePasswordStrength:
    """Test password strength validation."""

    def test_valid_password_with_number(self):
        """Test valid password with number."""
        assert (
            validate_password_strength("password123") is True
        )  # pragma: allowlist secret

    def test_valid_password_with_special_char(self):
        """Test valid password with special character."""
        assert (
            validate_password_strength("password!@#") is True
        )  # pragma: allowlist secret

    def test_password_too_short(self):
        """Test password that is too short."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("pass1")  # pragma: allowlist secret

    def test_password_no_number_or_special(self):
        """Test password without number or special character."""
        with pytest.raises(
            ValueError, match="at least one number or special character"
        ):
            validate_password_strength("password")  # pragma: allowlist secret

    def test_custom_min_length(self):
        """Test with custom minimum length."""
        assert (
            validate_password_strength("pass123", min_length=6) is True
        )  # pragma: allowlist secret

    def test_custom_min_length_too_short(self):
        """Test custom minimum length validation."""
        with pytest.raises(ValueError, match="at least 12 characters"):
            validate_password_strength(
                "password1", min_length=12
            )  # pragma: allowlist secret
