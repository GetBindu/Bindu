"""Tests for _setup_tunnel retry logic and failure handling."""

from unittest.mock import MagicMock, patch
import pytest

from bindu.penguin.bindufy import TunnelError, _setup_tunnel
from bindu.settings import app_settings

MAX_ATTEMPTS = app_settings.tunnel.max_attempts


def _make_tunnel_config():
    cfg = MagicMock()
    cfg.enabled = True
    cfg.subdomain = None
    return cfg


def _make_app_and_manifest():
    manifest = MagicMock()
    manifest.url = "http://localhost:3773"
    app = MagicMock()
    app.url = "http://localhost:3773"
    app._agent_card_json_schema = None
    return manifest, app


# ---------------------------------------------------------------------------
# Retry succeeds on second attempt
# ---------------------------------------------------------------------------

class TestTunnelRetrySuccess:
    @patch("bindu.tunneling.manager.TunnelManager")
    @patch("time.sleep")
    def test_succeeds_on_second_attempt(self, mock_sleep, mock_tm_cls):
        """Tunnel fails once then succeeds — should return URL with one retry."""
        tunnel_url = "https://abc.tunnel.example.com"

        mock_manager = mock_tm_cls.return_value
        mock_manager.create_tunnel.side_effect = [
            RuntimeError("connection refused"),  # attempt 1 fails
            tunnel_url,                          # attempt 2 succeeds
        ]

        manifest, app = _make_app_and_manifest()
        cfg = _make_tunnel_config()

        result_url, reason = _setup_tunnel(cfg, 3773, manifest, app, fail_on_tunnel_error=True)

        assert result_url == tunnel_url
        assert reason is None
        assert mock_manager.create_tunnel.call_count == 2
        mock_sleep.assert_called_once_with(
            app_settings.tunnel.base_backoff_seconds
        )


# ---------------------------------------------------------------------------
# All retries fail — hard error
# ---------------------------------------------------------------------------

class TestTunnelAllFailHardError:
    @patch("bindu.tunneling.manager.TunnelManager")
    @patch("time.sleep")
    def test_raises_tunnel_error_when_fail_on_error_true(self, mock_sleep, mock_tm_cls):
        """All retries exhausted with fail_on_tunnel_error=True → TunnelError raised."""
        mock_manager = mock_tm_cls.return_value
        mock_manager.create_tunnel.side_effect = RuntimeError("server unreachable")

        manifest, app = _make_app_and_manifest()
        cfg = _make_tunnel_config()

        with pytest.raises(TunnelError) as exc_info:
            _setup_tunnel(cfg, 3773, manifest, app, fail_on_tunnel_error=True)

        assert "server unreachable" in str(exc_info.value)
        assert mock_manager.create_tunnel.call_count == MAX_ATTEMPTS
        # No sleep after the final attempt
        assert mock_sleep.call_count == MAX_ATTEMPTS - 1


# ---------------------------------------------------------------------------
# All retries fail — soft fallback
# ---------------------------------------------------------------------------

class TestTunnelAllFailSoftFallback:
    @patch("bindu.tunneling.manager.TunnelManager")
    @patch("time.sleep")
    def test_returns_none_when_fail_on_error_false(self, mock_sleep, mock_tm_cls):
        """All retries exhausted with fail_on_tunnel_error=False → (None, reason) returned."""
        mock_manager = mock_tm_cls.return_value
        mock_manager.create_tunnel.side_effect = RuntimeError("timeout")

        manifest, app = _make_app_and_manifest()
        cfg = _make_tunnel_config()

        result_url, reason = _setup_tunnel(cfg, 3773, manifest, app, fail_on_tunnel_error=False)

        assert result_url is None
        assert "timeout" in reason
        assert mock_manager.create_tunnel.call_count == MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# Tunnel disabled — no-op
# ---------------------------------------------------------------------------

class TestTunnelDisabled:
    def test_returns_none_when_not_enabled(self):
        cfg = MagicMock()
        cfg.enabled = False
        manifest, app = _make_app_and_manifest()

        result_url, reason = _setup_tunnel(cfg, 3773, manifest, app)

        assert result_url is None
        assert reason is None
