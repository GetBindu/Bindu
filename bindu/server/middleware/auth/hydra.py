"""Hydra authentication middleware for Bindu server.

This middleware validates OAuth2 tokens issued by Ory Hydra for user authentication.
It inherits from AuthMiddleware and implements Hydra-specific token introspection.

Enhanced with hybrid OAuth2 + DID authentication for cryptographic identity verification.
"""

from __future__ import annotations as _annotations

import time
from typing import Any

from bindu.auth.hydra.client import HydraClient
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, jsonrpc_error
from bindu.utils.did_signature import (
    extract_signature_headers,
    verify_signature,
    get_public_key_from_hydra,
)

from .base import AuthMiddleware

logger = get_logger("bindu.server.middleware.hydra")


class HydraMiddleware(AuthMiddleware):
    """Hydra-specific authentication middleware with hybrid OAuth2 + DID authentication.

    This middleware implements dual-layer authentication:

    Layer 1 - OAuth2 Token Validation:
    - Token active status via Hydra Admin API
    - Token expiration (exp claim)
    - Token scope validation
    - Client ID validation

    Layer 2 - DID Signature Verification (optional):
    - Cryptographic signature verification using DID public key
    - Timestamp validation to prevent replay attacks
    - Request body integrity verification

    Supports both user authentication (authorization_code) and M2M (client_credentials).
    """

    def __init__(self, app: Any, auth_config: Any) -> None:
        """Initialize Hydra middleware.

        Args:
            app: ASGI application
            auth_config: Hydra authentication configuration
        """
        super().__init__(app, auth_config)
        self._introspection_cache = {}  # Simple token cache
        self._cache_ttl = 300  # 5 minutes cache TTL

    def _initialize_provider(self) -> None:
        """Initialize Hydra-specific components.

        Sets up:
        - HydraClient for token introspection
        - Hydra Admin API endpoint configuration
        """
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
        """Validate OAuth2 token using Hydra introspection.

        Args:
            token: OAuth2 access token issued by Hydra

        Returns:
            Decoded token introspection result

        Raises:
            Exception: If token is invalid, expired, or introspection fails
        """
        # Check cache first
        cache_key = token[:50]  # Use first 50 chars as cache key
        if cache_key in self._introspection_cache:
            cached = self._introspection_cache[cache_key]
            if cached["expires_at"] > time.time():
                logger.debug("Token validated from cache")
                return cached["data"]

        # Perform introspection via Hydra Admin API
        try:
            introspection_result = await self.hydra_client.introspect_token(token)

            if not introspection_result.get("active", False):
                raise ValueError("Token is not active")

            # Validate required fields
            if "sub" not in introspection_result:
                raise ValueError("Token missing subject (sub) claim")

            if "exp" not in introspection_result:
                raise ValueError("Token missing expiration (exp) claim")

            # Check expiration
            current_time = time.time()
            if introspection_result["exp"] < current_time:
                raise ValueError(f"Token expired at {introspection_result['exp']}")

            # Cache the result
            expires_at = min(
                introspection_result["exp"], current_time + self._cache_ttl
            )
            self._introspection_cache[cache_key] = {
                "data": introspection_result,
                "expires_at": expires_at,
            }

            # Clean old cache entries
            self._clean_cache()

            return introspection_result

        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise

    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user/service information from Hydra introspection result.

        Args:
            token_payload: Hydra token introspection result

        Returns:
            Dictionary with standardized user information:
            {
                "sub": "user_id or client_id",
                "is_m2m": True/False,
                "client_id": "oauth_client_id",
                "scope": ["scope1", "scope2"],
                "exp": expiration_timestamp,
                "iat": issued_at_timestamp,
                "aud": ["audience1", "audience2"],
                "username": "optional_username",
                "email": "optional_email",
                "name": "optional_full_name"
            }
        """
        # Determine if this is an M2M token
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

        # Extract additional user info from sub or extra claims
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

    async def _verify_did_signature(
        self, request: Any, client_did: str
    ) -> tuple[bool, dict[str, Any]]:
        """Verify DID signature on request (Layer 2 authentication).

        Args:
            request: Starlette Request object
            client_did: Client's DID from token

        Returns:
            Tuple of (is_valid, signature_info)
        """
        # Extract DID signature headers
        signature_data = extract_signature_headers(dict(request.headers))

        if not signature_data:
            # No DID signature headers present - this is optional for backward compatibility
            logger.debug("No DID signature headers found - skipping DID verification")
            return True, {"did_verified": False, "reason": "no_signature_headers"}

        # Verify DID matches token
        if signature_data["did"] != client_did:
            logger.warning(
                f"DID mismatch: header={signature_data['did']}, token={client_did}"
            )
            return False, {
                "did_verified": False,
                "reason": "did_mismatch",
                "header_did": signature_data["did"],
                "token_did": client_did,
            }

        # Get client's public key from Hydra metadata
        public_key = await get_public_key_from_hydra(client_did, self.hydra_client)

        if not public_key:
            logger.warning(f"No public key found for client: {client_did}")
            # If client has no public key, skip DID verification
            return True, {
                "did_verified": False,
                "reason": "no_public_key",
                "client_did": client_did,
            }

        # Read request body
        body = await request.body()

        # Verify signature
        is_valid = verify_signature(
            body=body,
            signature=signature_data["signature"],
            did=signature_data["did"],
            timestamp=signature_data["timestamp"],
            public_key=public_key,
            max_age_seconds=300,  # 5 minutes
        )

        if is_valid:
            logger.info(f"✅ DID signature verified for {client_did}")
            return True, {
                "did_verified": True,
                "did": client_did,
                "timestamp": signature_data["timestamp"],
            }
        else:
            logger.warning(f"❌ Invalid DID signature for {client_did}")
            return False, {
                "did_verified": False,
                "reason": "invalid_signature",
                "did": client_did,
            }

    async def dispatch(self, request, call_next):
        """Process request with hybrid OAuth2 + DID authentication.

        Flow:
        1. Check if endpoint is public
        2. Extract and validate OAuth2 token (Layer 1)
        3. Verify DID signature if present (Layer 2)
        4. Attach user context and continue

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response from endpoint or error response
        """
        from starlette.responses import JSONResponse

        path = request.url.path

        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"No token provided for {path}")
            return await self._auth_required_error(request)

        # Layer 1: Validate OAuth2 token
        try:
            token_payload = await self._validate_token(token)
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            return self._handle_validation_error(e, path)

        # Extract user info
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            from bindu.common.protocol.types import InvalidTokenError
            from bindu.utils.request_utils import extract_error_fields

            code, message = extract_error_fields(InvalidTokenError)
            return jsonrpc_error(code=code, message=message, status=401)

        # Layer 2: Verify DID signature (if present)
        client_did = user_info.get("client_id")

        # Check if client uses DID-based authentication
        if client_did and client_did.startswith("did:"):
            is_valid, signature_info = await self._verify_did_signature(
                request, client_did
            )

            if not is_valid:
                logger.warning(f"DID signature verification failed for {client_did}")
                return JSONResponse(
                    {
                        "error": "Invalid DID signature",
                        "details": signature_info,
                    },
                    status_code=403,
                )

            # Add signature info to user context
            user_info["signature_info"] = signature_info
            logger.debug(f"DID verification result: {signature_info}")

        # Attach context to request state
        self._attach_user_context(request, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, "
            f"m2m={user_info.get('is_m2m', False)}, "
            f"did_verified={user_info.get('signature_info', {}).get('did_verified', False)}"
        )

        return await call_next(request)

    def _clean_cache(self) -> None:
        """Clean expired entries from introspection cache."""
        current_time = time.time()
        expired_keys = [
            key
            for key, value in self._introspection_cache.items()
            if value["expires_at"] <= current_time
        ]
        for key in expired_keys:
            del self._introspection_cache[key]

    def _handle_validation_error(self, error: Exception, path: str) -> Any:
        """Handle Hydra-specific token validation errors.

        Args:
            error: Validation exception
            path: Request path

        Returns:
            JSON-RPC error response
        """
        error_str = str(error).lower()

        # Special handling for Hydra-specific errors
        if "connection refused" in error_str or "timeout" in error_str:
            logger.error(f"Hydra service unavailable for {path}: {error}")
            from bindu.common.protocol.types import InternalError

            code, message = extract_error_fields(InternalError)
            return jsonrpc_error(
                code=code,
                message="Authentication service temporarily unavailable",
                data=str(error),
                status=503,
            )
        elif "not active" in error_str:
            from bindu.common.protocol.types import InvalidTokenError

            code, message = extract_error_fields(InvalidTokenError)
            return jsonrpc_error(
                code=code,
                message="Token is not active or has been revoked",
                data=str(error),
                status=401,
            )

        # Fall back to base class error handling
        return super()._handle_validation_error(error, path)
