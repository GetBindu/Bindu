"""A2A middleware pipeline primitives and built-in middleware."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.jsonrpc_models import (
    JSONRPCErrorModel,
    JSONRPCErrorResponseModel,
)
from bindu.utils.request_utils import get_client_ip


class A2AMiddleware:
    """Base class for A2A middleware."""

    async def before_request(
        self, request: Request, payload: dict[str, Any]
    ) -> Response | None:
        return None

    async def after_response(
        self, request: Request, response: Response
    ) -> Response | None:
        return None

    async def on_error(self, request: Request, error: Exception | Response) -> Response | None:
        return None


def build_jsonrpc_error_response(
    code: int,
    message: str,
    detail: str | None = None,
    request_id: str | int | None = None,
    correlation_id: str | None = None,
    status: int = 400,
) -> JSONResponse:
    """Create a JSON-RPC error response with optional correlation details."""
    error_data: dict[str, str] | None = None
    if detail is not None or correlation_id is not None:
        error_data = {}
        if detail is not None:
            error_data["detail"] = detail
        if correlation_id is not None:
            error_data["request_id"] = correlation_id

    error_model = JSONRPCErrorResponseModel(
        error=JSONRPCErrorModel(code=code, message=message, data=error_data),
        id=str(request_id) if request_id is not None else None,
    )
    return JSONResponse(content=error_model.model_dump(), status_code=status)


class CorrelationIdMiddleware(A2AMiddleware):
    """Attach correlation IDs to requests and responses."""

    async def before_request(
        self, request: Request, payload: dict[str, Any]
    ) -> Response | None:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        return None

    async def after_response(
        self, request: Request, response: Response
    ) -> Response | None:
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    async def on_error(self, request: Request, error: Exception | Response) -> Response | None:
        if isinstance(error, Response):
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                error.headers["X-Request-ID"] = request_id
            return error
        return None


class TraceIdMiddleware(A2AMiddleware):
    """Attach trace IDs to requests and responses."""

    async def before_request(
        self, request: Request, payload: dict[str, Any]
    ) -> Response | None:
        trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
        request.state.trace_id = trace_id
        return None

    async def after_response(
        self, request: Request, response: Response
    ) -> Response | None:
        trace_id = getattr(request.state, "trace_id", None)
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        return response

    async def on_error(self, request: Request, error: Exception | Response) -> Response | None:
        if isinstance(error, Response):
            trace_id = getattr(request.state, "trace_id", None)
            if trace_id:
                error.headers["X-Trace-Id"] = trace_id
            return error
        return None


RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


class RateLimitMiddleware(A2AMiddleware):
    """Lightweight in-memory rate limiting for A2A requests."""

    def __init__(
        self,
        limit: int | None = None,
        window_seconds: int | None = None,
        clock: callable | None = None,
        bucket_store: dict[str, list[float]] | None = None,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.bucket_store = bucket_store if bucket_store is not None else RATE_LIMIT_BUCKETS

    async def before_request(
        self, request: Request, payload: dict[str, Any]
    ) -> Response | None:
        client_ip = get_client_ip(request)
        now = self.clock() if self.clock is not None else time.time()
        window_seconds = (
            self.window_seconds
            if self.window_seconds is not None
            else RATE_LIMIT_WINDOW_SECONDS
        )
        limit = self.limit if self.limit is not None else RATE_LIMIT_MAX_REQUESTS
        window_start = now - window_seconds
        bucket = self.bucket_store.setdefault(client_ip, [])
        bucket[:] = [entry for entry in bucket if entry >= window_start]
        if len(bucket) >= limit:
            request.state.error_type = "rate_limit"
            correlation_id = getattr(request.state, "request_id", None)
            return build_jsonrpc_error_response(
                -32000,
                "Rate limit exceeded. Try again later.",
                request_id=payload.get("id"),
                correlation_id=correlation_id,
                status=429,
            )
        bucket.append(now)
        return None


class StructuredLoggingMiddleware(A2AMiddleware):
    """Emit structured request logs for A2A traffic."""

    def __init__(self, logger_name: str = "bindu.server.endpoints.a2a_protocol") -> None:
        self.logger = logging.getLogger(logger_name)

    async def before_request(
        self, request: Request, payload: dict[str, Any]
    ) -> Response | None:
        request.state.a2a_start_time = time.perf_counter()
        request.state.a2a_method = payload.get("method")
        return None

    async def after_response(
        self, request: Request, response: Response
    ) -> Response | None:
        if getattr(request.state, "a2a_logged", False):
            return response
        self._log_request(
            request,
            response.status_code,
            error_type=getattr(request.state, "error_type", None),
        )
        request.state.a2a_logged = True
        return response

    async def on_error(self, request: Request, error: Exception | Response) -> Response | None:
        status_code = error.status_code if isinstance(error, Response) else 500
        self._log_request(
            request,
            status_code,
            error_type=getattr(request.state, "error_type", "internal"),
        )
        request.state.a2a_logged = True
        if isinstance(error, Response):
            return error
        return None

    def _log_request(
        self,
        request: Request,
        status_code: int,
        error_type: str | None,
    ) -> None:
        latency_ms = 0.0
        start = getattr(request.state, "a2a_start_time", None)
        if start is not None:
            latency_ms = (time.perf_counter() - start) * 1000

        log_payload = {
            "event": "a2a_request",
            "request_id": getattr(request.state, "request_id", None),
            "trace_id": getattr(request.state, "trace_id", None),
            "method": getattr(request.state, "a2a_method", None),
            "client_ip": get_client_ip(request),
            "latency_ms": round(latency_ms, 2),
            "duration_ms": round(latency_ms, 2),
            "status_code": status_code,
        }
        if error_type:
            log_payload["error_type"] = error_type
        self.logger.info(log_payload)
