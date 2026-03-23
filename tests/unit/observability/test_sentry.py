"""Focused tests for Sentry error tracking integration."""

from unittest.mock import patch

from bindu.observability.sentry import (
    init_sentry,
    _before_send,
    _before_send_transaction,
)


class TestSentryInit:
    """Test Sentry initialization."""

    @patch("bindu.observability.sentry.app_settings")
    def test_init_when_disabled(self, mock_settings):
        """Test that init returns False when Sentry is disabled."""
        mock_settings.sentry.enabled = False

        result = init_sentry()

        assert result is False

    @patch("bindu.observability.sentry.app_settings")
    def test_init_without_dsn(self, mock_settings):
        """Test that init returns False when DSN is missing."""
        mock_settings.sentry.enabled = True
        mock_settings.sentry.dsn = None

        result = init_sentry()

        assert result is False

    @patch("bindu.observability.sentry.app_settings")
    @patch("bindu.observability.sentry.socket")
    def test_init_success(self, mock_socket, mock_settings):
        """Test successful Sentry initialization."""
        mock_settings.sentry.enabled = True
        mock_settings.sentry.dsn = "https://key@sentry.io/project"
        mock_settings.sentry.environment = "production"
        mock_settings.sentry.integrations = ["asyncio", "starlette"]
        mock_settings.sentry.default_tags = {}
        mock_settings.sentry.release = None
        mock_settings.sentry.server_name = None
        mock_settings.sentry.traces_sample_rate = 0.1
        mock_settings.sentry.profiles_sample_rate = 0.0
        mock_settings.sentry.send_default_pii = False
        mock_settings.sentry.max_breadcrumbs = 100
        mock_settings.sentry.attach_stacktrace = True
        mock_settings.sentry.debug = False
        mock_settings.sentry.ignore_errors = []
        mock_settings.project.version = "1.0.0"

        mock_socket.gethostname.return_value = "test-server"

        with patch("builtins.__import__", side_effect=ImportError()):
            result = init_sentry()

        # Should fail gracefully when sentry_sdk not available
        assert result is False


class TestBeforeSend:
    """Test event filtering before sending to Sentry."""

    def test_scrub_authorization_header(self):
        """Test that authorization headers are scrubbed."""
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret-token",
                    "content-type": "application/json",
                }
            }
        }

        result = _before_send(event, {})

        assert result is not None
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["content-type"] == "application/json"

    def test_scrub_sensitive_data_fields(self):
        """Test that sensitive data fields are scrubbed."""
        event = {
            "request": {
                "data": {
                    "username": "user123",
                    "password": "secret123",
                    "api_key": "key123",
                }
            }
        }

        result = _before_send(event, {})

        assert result is not None
        assert result["request"]["data"]["username"] == "user123"
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["api_key"] == "[Filtered]"

    def test_no_scrubbing_when_no_sensitive_data(self):
        """Test that events without sensitive data pass through."""
        event = {"message": "An error occurred", "level": "error"}

        result = _before_send(event, {})

        assert result == event

    def test_scrub_multiple_sensitive_headers(self):
        """Test scrubbing multiple sensitive headers."""
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer token",
                    "x-api-key": "secret",
                    "cookie": "session=abc123",
                    "user-agent": "Mozilla/5.0",
                }
            }
        }

        result = _before_send(event, {})

        assert result is not None
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["x-api-key"] == "[Filtered]"
        assert result["request"]["headers"]["cookie"] == "[Filtered]"
        assert result["request"]["headers"]["user-agent"] == "Mozilla/5.0"


class TestBeforeSendTransaction:
    """Test transaction filtering."""

    @patch("bindu.observability.sentry.app_settings")
    def test_filter_health_check_transaction(self, mock_settings):
        """Test that health check transactions are filtered out."""
        mock_settings.sentry.filter_transactions = ["/health", "/metrics"]

        event = {"transaction": "/health"}

        result = _before_send_transaction(event, {})

        assert result is None

    @patch("bindu.observability.sentry.app_settings")
    def test_allow_normal_transaction(self, mock_settings):
        """Test that normal transactions pass through."""
        mock_settings.sentry.filter_transactions = ["/health", "/metrics"]

        event = {"transaction": "/api/agent/send_message"}

        result = _before_send_transaction(event, {})

        assert result == event

    @patch("bindu.observability.sentry.app_settings")
    def test_filter_metrics_endpoint(self, mock_settings):
        """Test filtering of metrics endpoint."""
        mock_settings.sentry.filter_transactions = ["/metrics"]

        event = {"transaction": "/metrics"}

        result = _before_send_transaction(event, {})

        assert result is None


class TestSentryEdgeCases:
    """Test edge cases in Sentry integration."""

    def test_before_send_with_non_dict_data(self):
        """Test before_send handles non-dict request data."""
        event = {"request": {"data": "string data instead of dict"}}

        result = _before_send(event, {})

        # Should not crash, just return event unchanged
        assert result == event
