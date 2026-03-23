"""Push notification delivery service for agent task events."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from bindu.common.protocol.types import PushNotificationConfig
from bindu.utils.logging import get_logger
from bindu.utils.retry import create_retry_decorator

logger = get_logger("bindu.utils.notifications")

# RFC-1918 private ranges, loopback, link-local, and cloud-metadata CIDRs that
# SSRF attackers commonly target.  Webhook URLs resolving into these ranges are
# rejected before any connection is attempted.
_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),  # loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC-1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC-1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC-1918
    ipaddress.ip_network(
        "169.254.0.0/16"
    ),  # link-local / cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


class NotificationDeliveryError(Exception):
    """Raised when a push notification cannot be delivered."""

    def __init__(self, status: int | None, message: str):
        """Initialize notification delivery error.

        Args:
            status: HTTP status code if available
            message: Error message
        """
        super().__init__(message)
        self.status = status


@dataclass
class NotificationService:
    """Deliver push notification events to configured HTTP endpoints.

    Includes lightweight in-memory delivery metrics for observability.
    Uses unified retry decorator for consistent retry behavior.
    """

    timeout: float = 5.0

    # --- Metrics ---
    total_sent: int = 0
    total_success: int = 0
    total_failures: int = 0

    async def send_event(
        self, config: PushNotificationConfig, event: dict[str, Any]
    ) -> None:
        """Send an event to the configured HTTP webhook."""
        self.validate_config(config)

        payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
        headers = self._build_headers(config)

        # Use unified retry decorator for consistent retry behavior
        await self._post_with_retry(config["url"], headers, payload, event)

    def validate_config(self, config: PushNotificationConfig) -> None:
        """Validate push notification configuration before use.

        In addition to URL structure checks this method resolves the hostname
        and rejects any address that falls within a private, loopback, link-local
        or cloud-metadata range to prevent Server-Side Request Forgery (SSRF).
        """
        parsed = urlparse(config["url"])
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Push notification URL must use http or https scheme.")
        if not parsed.netloc:
            raise ValueError("Push notification URL must include a network location.")

        # SSRF defence: resolve the hostname and reject internal/private addresses.
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Push notification URL must include a valid hostname.")
        try:
            resolved_ip = socket.getaddrinfo(hostname, None)[0][4][0]
            addr = ipaddress.ip_address(resolved_ip)
        except (socket.gaierror, ValueError) as exc:
            raise ValueError(
                f"Push notification URL hostname could not be resolved: {exc}"
            ) from exc

        for blocked in _BLOCKED_NETWORKS:
            if addr in blocked:
                raise ValueError(
                    f"Push notification URL resolves to a blocked address range "
                    f"({addr} is in {blocked}). Internal addresses are not allowed."
                )

    @create_retry_decorator("api", max_attempts=3, min_wait=0.5, max_wait=5.0)
    async def _post_with_retry(
        self, url: str, headers: dict[str, str], payload: bytes, event: dict[str, Any]
    ) -> None:
        """Send POST request with automatic retry via unified retry decorator."""
        # --- Metrics: count total attempts to send ---
        self.total_sent += 1

        try:
            status = await asyncio.to_thread(self._post_once, url, headers, payload)
            logger.debug(
                "Delivered push notification",
                event_id=event.get("event_id"),
                task_id=event.get("task_id"),
                status=status,
            )
            self.total_success += 1
        except NotificationDeliveryError as exc:
            # Don't retry 4xx client errors (except 429 rate limit)
            if exc.status is not None and 400 <= exc.status < 500 and exc.status != 429:
                logger.warning(
                    "Dropping push notification due to client error",
                    event_id=event.get("event_id"),
                    task_id=event.get("task_id"),
                    status=exc.status,
                    message=str(exc),
                )
                self.total_failures += 1
                raise

            # For retryable errors, let the decorator handle it
            logger.error(
                "Failed to deliver push notification",
                event_id=event.get("event_id"),
                task_id=event.get("task_id"),
                status=exc.status,
                message=str(exc),
            )
            self.total_failures += 1
            raise

    def _post_once(self, url: str, headers: dict[str, str], payload: bytes) -> int:
        req = request.Request(url, data=payload, method="POST")
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            # URL scheme is validated in validate_config() to only allow http/https
            with request.urlopen(req, timeout=self.timeout) as response:  # nosec B310
                status = response.getcode()
                if 200 <= status < 300:
                    return status
                raise NotificationDeliveryError(
                    status, f"Unexpected status code: {status}"
                )
        except error.HTTPError as exc:
            status = exc.code
            body = b""
            try:
                body = exc.read() or b""
            except OSError:
                body = b""
            message = body.decode("utf-8", errors="ignore").strip()
            raise NotificationDeliveryError(
                status, message or f"HTTP error {status}"
            ) from exc
        except error.URLError as exc:
            raise NotificationDeliveryError(
                None, f"Connection error: {exc.reason}"
            ) from exc

    def _build_headers(self, config: PushNotificationConfig) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_metrics(self) -> dict[str, int]:
        """Return delivery metrics for observability."""
        return {
            "total_sent": self.total_sent,
            "total_success": self.total_success,
            "total_failures": self.total_failures,
        }
