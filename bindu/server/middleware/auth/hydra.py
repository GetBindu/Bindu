"""Hydra authentication middleware for Bindu server.

This middleware validates OAuth2 tokens issued by Ory Hydra for user authentication.
It inherits from AuthMiddleware and implements Hydra-specific token introspection.
"""

from __future__ import annotations as _annotations

import time
from typing import Any

from bindu.auth.hydra_client import HydraClient
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, jsonrpc_error

from .base import AuthMiddleware

logger = get_logger("bindu.server.middleware.hydra")


class HydraMiddleware(AuthMiddleware):
    """Hydra-specific authentication middleware.

    This middleware implements Ory Hydra token introspection for OAuth2 tokens.
    It validates:
    - Token active status via Hydra Admin API
    - Token expiration (exp claim)
    - Token scope validation
    - Client ID validation

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
            code, message = extract_error_fields("ServiceUnavailableError")
            return jsonrpc_error(
                code=code,
                message="Authentication service temporarily unavailable",
                data=str(error),
                status=503,
            )
        elif "not active" in error_str:
            code, message = extract_error_fields("InvalidTokenError")
            return jsonrpc_error(
                code=code,
                message="Token is not active or has been revoked",
                data=str(error),
                status=401,
            )

        # Fall back to base class error handling
        return super()._handle_validation_error(error, path)

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        """Override dispatch to handle async token validation.

        Args:
            request: HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response from endpoint or error response
        """
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

        # Validate token - need to await since _validate_token is now async
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
            code, message = extract_error_fields("InvalidTokenError")
            return jsonrpc_error(code=code, message=message, status=401)

        # Attach context to request state
        self._attach_user_context(request, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, m2m={user_info.get('is_m2m', False)}"
        )

        return await call_next(request)
