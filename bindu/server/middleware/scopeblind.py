"""ScopeBlind authorization middleware for Bindu."""

from __future__ import annotations

import json

from opentelemetry.trace import get_current_span
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import InsufficientPermissionsError
from bindu.server.endpoints.utils import extract_error_fields, jsonrpc_error
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.scopeblind")

PROTECTED_PATH = "/"
PROTECTED_METHOD = "POST"


class ScopeBlindMiddleware(BaseHTTPMiddleware):
    """Evaluate Cedar policies before a task is submitted."""

    def __init__(self, app, scopeblind_ext):
        """Initialize ScopeBlind middleware."""
        super().__init__(app)
        self.scopeblind_ext = scopeblind_ext

    async def dispatch(self, request: Request, call_next) -> Response:
        """Authorize the incoming request and propagate receipt context."""
        if (
            not self.scopeblind_ext
            or request.url.path != PROTECTED_PATH
            or request.method != PROTECTED_METHOD
        ):
            return await call_next(request)

        try:
            body = await request.body()
            request_data = json.loads(body.decode("utf-8"))
            method = request_data.get("method", "")

            from starlette.requests import Request as StarletteRequest

            async def receive():
                return {"type": "http.request", "body": body}

            request = StarletteRequest(request.scope, receive)
        except Exception as error:
            logger.warning(
                "ScopeBlind middleware could not parse request body",
                error=str(error),
            )
            return await call_next(request)

        if method not in app_settings.scopeblind.protected_methods:
            return await call_next(request)

        decision = self.scopeblind_ext.evaluate_request(request, method, request_data)
        auth_context = decision.to_context(
            mode=self.scopeblind_ext.mode,
            policy_hash=self.scopeblind_ext.policy_hash,
            verification_key=self.scopeblind_ext.public_key_base58,
            issuer=self.scopeblind_ext.issuer,
        )
        request.state.scopeblind_context = auth_context
        self._set_span_attributes(auth_context)

        if not decision.allowed and self.scopeblind_ext.mode == "enforce":
            logger.warning(
                "ScopeBlind denied request in enforce mode",
                method=method,
                policy_ids=decision.policy_ids,
                errors=decision.errors,
            )
            code, message = extract_error_fields(InsufficientPermissionsError)
            return jsonrpc_error(
                code,
                message,
                "ScopeBlind denied this action under the configured Cedar policies.",
                request_id=request_data.get("id"),
                status=403,
            )

        if not decision.allowed:
            logger.warning(
                "ScopeBlind denied request in shadow mode; allowing execution",
                method=method,
                policy_ids=decision.policy_ids,
                errors=decision.errors,
            )

        return await call_next(request)

    @staticmethod
    def _set_span_attributes(auth_context: dict[str, object]) -> None:
        """Attach ScopeBlind metadata to the active span when available."""
        current_span = get_current_span()
        if current_span.is_recording():
            current_span.set_attribute(
                "bindu.scopeblind.decision",
                str(auth_context.get("decision", "")),
            )
            current_span.set_attribute(
                "bindu.scopeblind.mode",
                str(auth_context.get("mode", "")),
            )
            current_span.set_attribute(
                "bindu.scopeblind.policy_hash",
                str(auth_context.get("policy_hash", "")),
            )
