"""Unit tests for Sentry integration."""

from unittest.mock import patch

from bindu.observability import sentry
from bindu.settings import app_settings


class TestSentryInit:
    """Test Sentry initialization."""

    def test_init_sentry_disabled(self):
        """Test that Sentry doesn't initialize when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_no_dsn(self):
        """Test that Sentry doesn't initialize without DSN."""
        with (
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", ""),
        ):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_success(self):
        """Test successful Sentry initialization."""
        with (
            patch("sentry_sdk.init") as mock_init,
            patch("sentry_sdk.set_tag"),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
            patch.object(app_settings.sentry, "environment", "test"),
            patch.object(app_settings.sentry, "integrations", ["starlette", "asyncio"]),
        ):
            result = sentry.init_sentry()
            assert result is True
            mock_init.assert_called_once()

    def test_init_sentry_with_release(self):
        """Test Sentry initialization with custom release."""
        with (
            patch("sentry_sdk.init") as mock_init,
            patch("sentry_sdk.set_tag"),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
            patch.object(app_settings.sentry, "release", "my-app@1.0.0"),
            patch.object(app_settings.sentry, "integrations", ["starlette"]),
        ):
            result = sentry.init_sentry()
            assert result is True
            # Check that release was passed
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["release"] == "my-app@1.0.0"

    def test_init_sentry_import_error(self):
        """Test Sentry initialization handles import errors."""
        with (
            patch("sentry_sdk.init", side_effect=ImportError("sentry_sdk not found")),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
        ):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_general_error(self):
        """Test Sentry initialization handles general errors."""
        with (
            patch("sentry_sdk.init", side_effect=ValueError("Unexpected error")),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
        ):
            result = sentry.init_sentry()
            assert result is False


class TestSentryHooks:
    """Test Sentry before_send hooks."""

    def test_before_send_scrubs_headers(self):
        """Test that before_send scrubs sensitive headers."""
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret_token",
                    "x-api-key": "api_key_123",
                    "cookie": "session=abc123",
                    "content-type": "application/json",
                }
            }
        }

        result = sentry._before_send(event, {})

        assert result is not None
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["x-api-key"] == "[Filtered]"
        assert result["request"]["headers"]["cookie"] == "[Filtered]"
        assert result["request"]["headers"]["content-type"] == "application/json"

    def test_before_send_scrubs_data(self):
        """Test that before_send scrubs sensitive data."""
        event = {
            "request": {
                "data": {
                    "password": "secret123",  # pragma: allowlist secret
                    "token": "token_abc",
                    "api_key": "key_xyz",  # pragma: allowlist secret
                    "username": "john_doe",
                }
            }
        }

        result = sentry._before_send(event, {})

        assert result is not None
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["token"] == "[Filtered]"
        assert result["request"]["data"]["api_key"] == "[Filtered]"
        assert result["request"]["data"]["username"] == "john_doe"

    def test_before_send_transaction_filters(self):
        """Test that before_send_transaction filters health checks."""
        with patch.object(
            app_settings.sentry, "filter_transactions", ["/healthz", "/metrics"]
        ):
            # Health check should be filtered
            event = {"transaction": "/healthz"}
            result = sentry._before_send_transaction(event, {})
            assert result is None

            # Metrics should be filtered
            event = {"transaction": "/metrics"}
            result = sentry._before_send_transaction(event, {})
            assert result is None

            # Normal endpoint should not be filtered
            event = {"transaction": "/api/tasks"}
            result = sentry._before_send_transaction(event, {})
            assert result is not None
            assert result["transaction"] == "/api/tasks"

    def test_before_send_no_request(self):
        """Test that before_send handles events without request."""
        event = {"message": "Test error"}
        result = sentry._before_send(event, {})
        assert result == event

    def test_before_send_transaction_no_transaction(self):
        """Test that before_send_transaction handles events without transaction."""
        event = {"message": "Test"}
        result = sentry._before_send_transaction(event, {})
        assert result == event
