"""Tests for _setup_tunnel retry logic and failure handling."""

from unittest.mock import MagicMock, patch, call
import pytest

from bindu.penguin.bindufy import TunnelError, _setup_tunnel, _TUNNEL_MAX_ATTEMPTS


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
    @patch("bindu.penguin.bindufy.TunnelManager")
    @patch("httpx.get")
    @patch("time.sleep")
    def test_succeeds_on_second_attempt(self, mock_sleep, mock_httpx_get, mock_tm_cls):
        """Tunnel fails once then succeeds — should return URL with one retry."""
        tunnel_url = "https://abc.tunnel.example.com"

        mock_manager = mock_tm_cls.return_value
        mock_manager.create_tunnel.side_effect = [
            RuntimeError("connection refused"),  # attempt 1 fails
            tunnel_url,                          # attempt 2 succeeds
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_get.return_value = mock_response

        manifest, app = _make_app_and_manifest()
        cfg = _make_tunnel_config()

        result_url, reason = _setup_tunnel(cfg, 3773, manifest, app, fail_on_tunnel_error=True)

        assert result_url == tunnel_url
        assert reason is None
        assert mock_manager.create_tunnel.call_count == 2
        mock_sleep.assert_called_once_with(1)  # backoff after attempt 1


# ---------------------------------------------------------------------------
# All retries fail — hard error
# ---------------------------------------------------------------------------

class TestTunnelAllFailHardError:
    @patch("bindu.penguin.bindufy.TunnelManager")
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
        assert mock_manager.create_tunnel.call_count == _TUNNEL_MAX_ATTEMPTS
        assert mock_sleep.call_count == _TUNNEL_MAX_ATTEMPTS - 1  # no sleep after last attempt


# ---------------------------------------------------------------------------
# All retries fail — soft fallback
# ---------------------------------------------------------------------------

class TestTunnelAllFailSoftFallback:
    @patch("bindu.penguin.bindufy.TunnelManager")
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
        assert mock_manager.create_tunnel.call_count == _TUNNEL_MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# Health check failure triggers retry
# ---------------------------------------------------------------------------

class TestTunnelHealthCheckFailure:
    @patch("bindu.penguin.bindufy.TunnelManager")
    @patch("httpx.get")
    @patch("time.sleep")
    def test_bad_health_status_triggers_retry(self, mock_sleep, mock_httpx_get, mock_tm_cls):
        """Health check returning non-200 should count as a failed attempt."""
        tunnel_url = "https://abc.tunnel.example.com"

        mock_manager = mock_tm_cls.return_value
        mock_manager.create_tunnel.return_value = tunnel_url

        bad_response = MagicMock()
        bad_response.status_code = 502
        good_response = MagicMock()
        good_response.status_code = 200

        mock_httpx_get.side_effect = [bad_response, bad_response, bad_response, bad_response, bad_response, good_response]

        manifest, app = _make_app_and_manifest()
        cfg = _make_tunnel_config()

        result_url, reason = _setup_tunnel(cfg, 3773, manifest, app, fail_on_tunnel_error=True)

        assert result_url == tunnel_url
        assert reason is None
        assert mock_httpx_get.call_count == 6


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
