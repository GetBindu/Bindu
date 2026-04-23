"""Hydra authentication middleware for Bindu server.

This middleware acts as the primary gatekeeper for the application.
It intercepts incoming requests and validates OAuth2 tokens issued by Ory Hydra.

Enhanced with hybrid OAuth2 + DID authentication for cryptographic identity verification,
ensuring both authorization (who they are) and payload integrity (has the request been tampered with).
Refactored to Pure ASGI to prevent stream deadlocks during DID verification.
"""

from __future__ import annotations as _annotations

import asyncio
import hashlib
import time
import inspect
from typing import Any, Callable

from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket

from bindu.auth.hydra.client import HydraClient
from bindu.utils.logging import get_logger
from bindu.server.endpoints.utils import extract_error_fields, jsonrpc_error
from bindu.utils.did import (
    extract_signature_headers,
    verify_signature,
)

from .base import AuthMiddleware

logger = get_logger("bindu.server.middleware.hydra")

# Constants
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_BODY_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_SIGNATURE_AGE_SECONDS = 300  # 5 minutes


class HydraMiddleware(AuthMiddleware):
    """Hydra-specific authentication middleware with hybrid OAuth2 + DID authentication."""

    def __init__(self, app: Any, auth_config: Any) -> None:
        """Initialize Hydra middleware."""
        super().__init__(app, auth_config)

        self._introspection_cache = {}
        self._cache_locks = {}
        self._cache_ttl = CACHE_TTL_SECONDS
        self._max_body_size = MAX_BODY_SIZE_BYTES

    def _initialize_provider(self) -> None:
        """Initialize Hydra-specific components and HTTP clients."""
        try:
            self.hydra_client = HydraClient(
                admin_url=self.config.admin_url,
                public_url=getattr(self.config, "public_url", None),
                timeout=getattr(self.config, "timeout", 10),
                verify_ssl=getattr(self.config, "verify_ssl", True),
            )
            logger.info(
                f"Hydra middleware initialized. Admin URL: {self.config.admin_url}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Hydra client: {e}")
            raise

    async def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate OAuth2 token using Hydra introspection."""
        cache_key = hashlib.sha256(token.encode()).hexdigest()
        if cache_key in self._introspection_cache:
            cached = self._introspection_cache[cache_key]
            if cached["expires_at"] > time.time():
                logger.debug("Token validated from cache")
                return cached["data"]

        try:
            introspection_result = await self.hydra_client.introspect_token(token)

            if not introspection_result.get("active", False):
                raise ValueError("Token is not active")
            if "sub" not in introspection_result:
                raise ValueError("Token missing subject (sub) claim")
            if "exp" not in introspection_result:
                raise ValueError("Token missing expiration (exp) claim")

            current_time = time.time()
            if introspection_result["exp"] < current_time:
                raise ValueError(f"Token expired at {introspection_result['exp']}")

            expires_at = min(
                introspection_result["exp"], current_time + self._cache_ttl
            )
            self._introspection_cache[cache_key] = {
                "data": introspection_result,
                "expires_at": expires_at,
            }

            self._lazy_clean_cache()
            return introspection_result
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise

    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize Hydra introspection data into a standard user/service object."""
        is_m2m = (
            token_payload.get("token_type") == "access_token"
            and token_payload.get("grant_type") == "client_credentials"
        )

        user_info = {
            "sub": token_payload["sub"],
            "is_m2m": is_m2m,
            "client_id": token_payload.get("client_id", ""),
            "scope": token_payload.get("scope", "").split()
            if token_payload.get("scope")
            else [],
            "exp": token_payload.get("exp", 0),
            "iat": token_payload.get("iat", 0),
            "aud": token_payload.get("aud", []),
            "token_type": token_payload.get("token_type", ""),
            "grant_type": token_payload.get("grant_type", ""),
            "active": token_payload.get("active", False),
        }

        if not is_m2m and "ext" in token_payload:
            ext_data = token_payload["ext"]
            if isinstance(ext_data, dict):
                user_info.update(
                    {
                        "username": ext_data.get("username"),
                        "email": ext_data.get("email"),
                        "name": ext_data.get("name"),
                        "preferred_username": ext_data.get("preferred_username"),
                    }
                )

        logger.debug(f"Extracted user info for sub={user_info['sub']}, is_m2m={is_m2m}")
        return user_info

    def _lazy_clean_cache(self) -> None:
        """O(1) amortized cache cleanup."""
        current_time = time.time()
        expired_keys = []

        for key, value in self._introspection_cache.items():
            if value["expires_at"] <= current_time:
                expired_keys.append(key)
            else:
                break

        for key in expired_keys:
            self._introspection_cache.pop(key, None)
            self._cache_locks.pop(key, None)

    async def _verify_did_signature_asgi(
        self, receive: Callable, client_did: str, headers: Any
    ) -> tuple[bool, dict[str, Any], Callable]:
        """Safely verify DID signature by buffering the raw ASGI receive stream.

        Contract: this function is only invoked for callers whose OAuth
        ``client_id`` starts with ``did:`` — the outer ``__call__`` gate in
        :meth:`HydraMiddleware.__call__` enforces that. At that point the
        DID-signed request envelope is mandatory; there is no fallback to
        "unsigned is fine." Previously this function failed open (returned
        ``is_valid=True``) when signature headers were absent or when Hydra
        had no public key for the client — both treated as "can't verify, so
        allow." That reduced DID signing to a header the caller could simply
        omit. See ``bugs/2026-04-18-did-signature-fail-open.md``.
        """
        signature_data = extract_signature_headers(dict(headers))

        if not signature_data:
            # Caller is a DID client but sent no X-DID-Signature. Reject —
            # signing is mandatory once client_id is a DID.
            logger.warning(
                f"DID client {client_did} sent request without signature "
                f"headers; signing is mandatory for did:* clients."
            )
            return (
                False,
                {"did_verified": False, "reason": "missing_signature_headers"},
                receive,
            )

        if signature_data["did"] != client_did:
            return False, {"did_verified": False, "reason": "did_mismatch"}, receive

        public_key = await self.hydra_client.get_public_key_from_client(client_did)
        if not public_key:
            # Hydra client metadata has no public_key — the signature can't
            # be verified. Reject rather than wave the request through. An
            # operator who registered a DID client without a public key in
            # metadata has a configuration bug that must be fixed explicitly.
            logger.warning(
                f"No public key in Hydra metadata for DID client {client_did}; "
                f"signature verification cannot proceed. Register the client's "
                f"base58 Ed25519 public key under metadata.public_key."
            )
            return (
                False,
                {"did_verified": False, "reason": "public_key_unavailable"},
                receive,
            )

        # Memory Safety Guard
        content_length = int(headers.get("content-length", 0))
        if content_length > MAX_BODY_SIZE_BYTES:
            logger.warning(
                f"Payload too large for signature verification: {content_length} bytes"
            )
            return (
                False,
                {"did_verified": False, "reason": "payload_too_large"},
                receive,
            )

        # Safely buffer the ASGI stream chunks
        body = b""
        more_body = True
        messages = []
        while more_body:
            message = await receive()
            messages.append(message)
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        # Create a proxy receiver to feed the downstream application
        async def cached_receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        # Background thread crypto validation to prevent event loop blocking
        is_valid = await asyncio.to_thread(
            verify_signature,
            body=body,
            signature=signature_data["signature"],
            did=signature_data["did"],
            timestamp=signature_data["timestamp"],
            public_key=public_key,
            max_age_seconds=MAX_SIGNATURE_AGE_SECONDS,
        )

        verification_result = {
            "did_verified": is_valid,
            "did": client_did,
            "timestamp": signature_data.get("timestamp"),
            "reason": None if is_valid else "invalid_signature",
        }
        return is_valid, verification_result, cached_receive

    async def __call__(
        self, scope: dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        """Hydra-specific Pure ASGI pipeline overriding the base class."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        conn = HTTPConnection(scope)
        path = conn.url.path

        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            await self.app(scope, receive, send)
            return

        token = self._extract_token(conn)
        if not token:
            from bindu.common.protocol.types import AuthenticationRequiredError

            await self._send_error(
                scope, receive, send, AuthenticationRequiredError, 401
            )
            return

        try:
            result = self._validate_token(token)
            token_payload = await result if inspect.isawaitable(result) else result
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            await self._handle_validation_error(e, path, scope, receive, send)
            return

        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            from bindu.common.protocol.types import InvalidTokenError

            await self._send_error(scope, receive, send, InvalidTokenError, 401)
            return

        # --- LAYER 2: ASGI Safe DID Verification ---
        client_did = user_info.get("client_id")
        if scope["type"] == "http" and client_did and client_did.startswith("did:"):
            is_valid, signature_info, receive = await self._verify_did_signature_asgi(
                receive, client_did, conn.headers
            )

            if not is_valid:
                logger.warning(f"DID signature verification failed for {client_did}")
                response = JSONResponse(
                    {"error": "Invalid DID signature", "details": signature_info},
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            user_info["signature_info"] = signature_info
            logger.debug(f"DID verification result: {signature_info}")

        self._attach_user_context(scope, user_info, token_payload)
        await self.app(scope, receive, send)

    async def _handle_validation_error(
        self,
        error: Exception,
        path: str,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        """Map raw exceptions to standard JSON-RPC error responses (Pure ASGI)."""
        error_str = str(error).lower()

        if "connection refused" in error_str or "timeout" in error_str:
            logger.error(f"Hydra service unavailable for {path}: {error}")
            from bindu.common.protocol.types import InternalError

            code, _ = extract_error_fields(InternalError)
            response = jsonrpc_error(
                code=code,
                message="Authentication service temporarily unavailable",
                data=str(error),
                status=503,
            )

            if scope["type"] == "websocket":
                ws = WebSocket(scope, receive, send)
                await ws.accept()
                await ws.close(code=1011, reason="Auth service unavailable")
            else:
                await response(scope, receive, send)
            return

        elif "not active" in error_str:
            from bindu.common.protocol.types import InvalidTokenError

            code, _ = extract_error_fields(InvalidTokenError)
            response = jsonrpc_error(
                code=code,
                message="Token is not active or has been revoked",
                data=str(error),
                status=401,
            )

            if scope["type"] == "websocket":
                ws = WebSocket(scope, receive, send)
                await ws.accept()
                await ws.close(code=1008, reason="Token not active")
            else:
                await response(scope, receive, send)
            return

        await super()._handle_validation_error(error, path, scope, receive, send)
