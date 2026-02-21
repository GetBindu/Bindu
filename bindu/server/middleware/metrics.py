"""Metrics middleware for tracking HTTP requests."""

from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bindu.server.metrics import get_metrics
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.metrics")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response
        """
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        metrics = get_metrics()

        # Increment requests in flight
        metrics.increment_requests_in_flight()

        try:
            # Get request size
            request_size = 0
            if request.headers.get("content-length"):
                try:
                    request_size = int(request.headers["content-length"])
                except (ValueError, TypeError):
                    pass

            # Record start time
            start_time = time.time()

            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Get response size
            response_size = 0
            if response.headers.get("content-length"):
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, TypeError):
                    pass

            # Record metrics
            try:
                method = request.method
                # Sanitize endpoint to avoid high cardinality
                # Replace UUIDs and numeric IDs with placeholders
                import re

                endpoint = request.url.path
                endpoint = re.sub(
                    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                    "/:id",
                    endpoint,
                )
                endpoint = re.sub(r"/\d+", "/:id", endpoint)

                status = str(response.status_code)

                metrics.record_http_request(
                    method,
                    endpoint,
                    status,
                    duration,
                    request_size=request_size,
                    response_size=response_size,
                )

                logger.debug(
                    f"Recorded metrics: {method} {endpoint} {status} "
                    f"{duration:.3f}s req={request_size}B resp={response_size}B"
                )
            except Exception as e:
                logger.error(f"Failed to record metrics: {e}")

            return response
        finally:
            # Always decrement requests in flight
            metrics.decrement_requests_in_flight()
