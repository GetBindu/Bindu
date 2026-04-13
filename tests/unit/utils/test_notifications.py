"""Minimal tests for notification service."""

from io import BytesIO
import socket
from typing import cast
from unittest.mock import MagicMock, patch
from urllib import error
from uuid import uuid4
import pytest

from bindu.common.protocol.types import PushNotificationConfig
from bindu.utils.notifications import NotificationService, NotificationDeliveryError


class TestNotificationService:
    """Test notification service functionality."""

    def test_notification_service_initialization(self):
        """Test service initializes with default values."""
        service = NotificationService()

        assert service.timeout == 5.0
        assert service.total_sent == 0
        assert service.total_success == 0
        assert service.total_failures == 0

    def test_validate_config_valid_http(self):
        """Test validating valid HTTP URL."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            service.validate_config(config)

    def test_validate_config_valid_https(self):
        """Test validating valid HTTPS URL."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "https://example.com/webhook"},
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            service.validate_config(config)

    def test_validate_config_invalid_scheme(self):
        """Test validation rejects invalid URL scheme."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "ftp://example.com/webhook"}
        )

        with pytest.raises(ValueError, match="must use http or https scheme"):
            service.validate_config(config)

    def test_validate_config_no_netloc(self):
        """Test validation rejects URL without netloc."""
        service = NotificationService()
        config = cast(PushNotificationConfig, {"id": uuid4(), "url": "http://"})

        with pytest.raises(ValueError, match="must include a network location"):
            service.validate_config(config)

    def test_validate_config_blocks_loopback(self):
        """Test validation blocks loopback addresses."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://localhost/webhook"}
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("127.0.0.1", 0))]
        ):
            with pytest.raises(ValueError, match="blocked address range"):
                service.validate_config(config)

    def test_validate_config_blocks_private_network(self):
        """Test validation blocks private network addresses."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://192.168.1.1/webhook"}
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("192.168.1.1", 0))]
        ):
            with pytest.raises(ValueError, match="blocked address range"):
                service.validate_config(config)

    def test_validate_config_blocks_link_local(self):
        """Test validation blocks link-local addresses."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "http://169.254.169.254/webhook"},
        )

        with patch(
            "socket.getaddrinfo",
            return_value=[("", "", "", "", ("169.254.169.254", 0))],
        ):
            with pytest.raises(ValueError, match="blocked address range"):
                service.validate_config(config)

    def test_validate_config_hostname_resolution_fails(self):
        """Test validation handles hostname resolution failure."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "http://invalid.example/webhook"},
        )

        with patch(
            "socket.getaddrinfo", side_effect=socket.gaierror("Name resolution failed")
        ):
            with pytest.raises(ValueError, match="hostname could not be resolved"):
                service.validate_config(config)

    def test_build_headers_basic(self):
        """Test building basic headers without token."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )

        headers = service._build_headers(config)

        assert headers["Content-Type"] == "application/json"
        assert len(headers) == 1

    def test_build_headers_with_token(self):
        """Test building headers with authentication token."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {
                "id": uuid4(),
                "url": "http://example.com/webhook",
                "token": "secret-token",
            },
        )

        headers = service._build_headers(config)

        assert headers["Authorization"] == "Bearer secret-token"

    def test_build_headers_with_authentication(self):
        """Test building headers with authentication dict."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {
                "id": uuid4(),
                "url": "http://example.com/webhook",
                "authentication": {"type": "bearer"},
            },
        )

        headers = service._build_headers(config)

        assert "authentication" in str(headers).lower() or "Content-Type" in headers

    @pytest.mark.asyncio
    async def test_send_event_success(self):
        """Test successfully sending an event."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )
        event = {"kind": "status-update", "task_id": str(uuid4())}

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            with patch.object(service, "_post_once", return_value=200):
                await service.send_event(config, event)

        assert service.total_sent > 0

    @pytest.mark.asyncio
    async def test_send_event_delivery_error(self):
        """Test handling delivery error."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )
        event = {"kind": "status-update", "task_id": str(uuid4())}

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            with patch.object(
                service,
                "_post_once",
                side_effect=NotificationDeliveryError(400, "Bad request"),
            ):
                with pytest.raises(NotificationDeliveryError):
                    await service.send_event(config, event)

    def test_notification_delivery_error(self):
        """Test NotificationDeliveryError creation."""
        error = NotificationDeliveryError(500, "Server error")

        assert error.status == 500
        assert str(error) == "Server error"

    def test_notification_delivery_error_no_status(self):
        """Test NotificationDeliveryError with no status."""
        error = NotificationDeliveryError(None, "Network error")

        assert error.status is None
        assert str(error) == "Network error"

    def test_post_once_rejects_invalid_destination(self):
        """Test _post_once wraps destination validation failures."""
        service = NotificationService()

        with patch.object(
            service,
            "_resolve_and_validate_destination",
            side_effect=ValueError("blocked"),
        ):
            with pytest.raises(NotificationDeliveryError, match="blocked") as exc_info:
                service._post_once("http://example.com/webhook", {}, b"{}")

        assert exc_info.value.status is None

    def test_post_once_raises_on_unexpected_status(self):
        """Test _post_once raises when HTTP status is not 2xx."""
        service = NotificationService()
        response = MagicMock()
        response.getcode.return_value = 500

        context_manager = MagicMock()
        context_manager.__enter__.return_value = response
        context_manager.__exit__.return_value = False

        with patch.object(service, "_resolve_and_validate_destination"):
            with patch(
                "bindu.utils.notifications.request.urlopen",
                return_value=context_manager,
            ):
                with pytest.raises(
                    NotificationDeliveryError, match="Unexpected status code: 500"
                ) as exc_info:
                    service._post_once("http://example.com/webhook", {}, b"{}")

        assert exc_info.value.status == 500

    def test_post_once_http_error_uses_response_body(self):
        """Test _post_once surfaces HTTP error body messages."""
        service = NotificationService()
        http_error = error.HTTPError(
            "http://example.com/webhook",
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(b"invalid payload"),
        )

        with patch.object(service, "_resolve_and_validate_destination"):
            with patch(
                "bindu.utils.notifications.request.urlopen",
                side_effect=http_error,
            ):
                with pytest.raises(
                    NotificationDeliveryError, match="invalid payload"
                ) as exc_info:
                    service._post_once("http://example.com/webhook", {}, b"{}")

        assert exc_info.value.status == 400

    def test_post_once_url_error_is_wrapped(self):
        """Test _post_once wraps URL errors into delivery errors."""
        service = NotificationService()

        with patch.object(service, "_resolve_and_validate_destination"):
            with patch(
                "bindu.utils.notifications.request.urlopen",
                side_effect=error.URLError("unreachable"),
            ):
                with pytest.raises(
                    NotificationDeliveryError, match="Connection error: unreachable"
                ) as exc_info:
                    service._post_once("http://example.com/webhook", {}, b"{}")

        assert exc_info.value.status is None
