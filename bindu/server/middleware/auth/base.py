"""Base authentication middleware interface for Bindu server.

Provides an abstract base class for authentication middleware.
Refactored to Pure ASGI for high throughput, WebSocket support, and DoS resistance.
"""

from __future__ import annotations as _annotations

import fnmatch
import re
import inspect
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket

from bindu.common.protocol.types import (
    AuthenticationRequiredError,
    InvalidTokenError,
    InvalidTokenSignatureError,
    TokenExpiredError,
)
from bindu.utils.logging import get_logger
from bindu.server.endpoints.utils import extract_error_fields, jsonrpc_error

logger = get_logger("bindu.server.middleware.auth.base")


class AuthMiddleware(ABC):
    """Abstract authentication middleware for Bindu server (Pure ASGI).

    Handles token extraction, validation, and user context attachment.
    Subclasses implement provider-specific validation logic.
    """

    def __init__(self, app: Callable, auth_config: Any) -> None:
        """Initialize authentication middleware.

        Args:
            app: The next ASGI application in the pipeline
            auth_config: Provider-specific authentication configuration
        """
        self.app = app
        self.config = auth_config

        # 1. Performance Optimization: Compile regex patterns on startup
        # instead of evaluating fnmatch on every incoming request.
        self._public_patterns = []
        public_endpoints = getattr(self.config, "public_endpoints", [])
        for pattern in public_endpoints:
            regex_str = fnmatch.translate(pattern)
            self._public_patterns.append(re.compile(regex_str))

        self._initialize_provider()

    # Abstract methods - Provider-specific implementation required

    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components (JWKS client, validators, etc.)."""

    @abstractmethod
    def _validate_token(self, token: str) -> dict[str, Any] | Awaitable[dict[str, Any]]:
        """Validate authentication token.

        Can be synchronous or asynchronous.
        """

    @abstractmethod
    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract standardized user information from token payload."""

    # Token extraction and validation helpers

    def _is_public_endpoint(self, path: str) -> bool:
        """O(1) Check if request path is a public endpoint using pre-compiled regex."""
        return any(pattern.match(path) for pattern in self._public_patterns)

    def _extract_token(self, conn: HTTPConnection) -> str | None:
        """Extract token from Header, WebSocket subprotocol, or Query Params."""
        # 1. Standard Authorization Header
        auth_header = conn.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]

        # 2. Query Parameter Fallback (Essential for strict WebSocket/SSE clients)
        token_query = conn.query_params.get("token")
        if token_query:
            return token_query

        # 3. WebSocket Protocol Fallback
        if conn.scope["type"] == "websocket":
            protocols = conn.headers.get("sec-websocket-protocol", "")
            for protocol in protocols.split(","):
                protocol = protocol.strip()
                if protocol.startswith("bearer-"):
                    return protocol[7:]

        return None

    # Main ASGI Dispatch

    async def __call__(
        self, scope: dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        """Pure ASGI implementation bypassing BaseHTTPMiddleware limitations."""
        # We only care about HTTP and WebSocket connections
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # HTTPConnection is a lightweight wrapper that handles both HTTP and WS scopes safely
        conn = HTTPConnection(scope)
        path = conn.url.path

        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            await self.app(scope, receive, send)
            return

        # Extract token
        token = self._extract_token(conn)
        if not token:
            logger.warning(f"No token provided for {path}")
            await self._send_error(
                scope, receive, send, AuthenticationRequiredError, 401
            )
            return

        # Validate token
        token_payload: dict[str, Any]
        try:
            # Safely support both async (Hydra) and sync validation implementations
            result = self._validate_token(token)
            if inspect.isawaitable(result):
                from typing import cast

                token_payload = cast(dict[str, Any], await result)
            else:
                token_payload = result
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            await self._handle_validation_error(e, path, scope, receive, send)
            return

        # Extract user info
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            await self._send_error(scope, receive, send, InvalidTokenError, 401)
            return

        # Attach context to ASGI state
        self._attach_user_context(scope, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, m2m={user_info.get('is_m2m', False)}"
        )

        # Pass the unconsumed stream to the next application
        await self.app(scope, receive, send)

    # Error handling and utilities

    async def _send_error(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
        error_type: Any,
        status: int,
        data: Any = None,
    ) -> None:
        """Send error response safely for both HTTP and WebSockets without parsing the body."""
        code, message = extract_error_fields(error_type)

        # JSON-RPC 2.0 states ID must be null on parse/auth errors
        # This prevents the DoS vector of parsing massive unauthenticated bodies
        response = jsonrpc_error(
            code=code, message=message, request_id=None, data=data, status=status
        )

        if scope["type"] == "websocket":
            # Safely reject unauthenticated websockets
            ws = WebSocket(scope, receive, send)
            await ws.accept()
            await ws.close(code=1008, reason=message)  # 1008 = Policy Violation
        else:
            await response(scope, receive, send)

    def _attach_user_context(
        self,
        scope: dict[str, Any],
        user_info: dict[str, Any],
        token_payload: dict[str, Any],
    ) -> None:
        """Attach user context to ASGI state dictionary."""
        scope.setdefault("state", {})
        scope["state"]["user"] = user_info
        scope["state"]["authenticated"] = True
        scope["state"]["token_payload"] = token_payload

    async def _handle_validation_error(
        self,
        error: Exception,
        path: str,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        """Handle token validation errors with appropriate error responses."""
        error_str = str(error).lower()

        if "expired" in error_str:
            error_type = TokenExpiredError
        elif "signature" in error_str:
            error_type = InvalidTokenSignatureError
        else:
            error_type = InvalidTokenError

        data = None if "expired" in error_str else f"Token validation failed: {error}"
        await self._send_error(scope, receive, send, error_type, 401, data=data)
