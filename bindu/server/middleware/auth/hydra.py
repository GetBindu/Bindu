"""Hydra authentication middleware for Bindu server.

This middleware acts as the primary gatekeeper for the application, similar to a
global authentication middleware in Express or Hono. It intercepts incoming requests
and validates OAuth2 tokens issued by Ory Hydra.

Enhanced with hybrid OAuth2 + DID authentication for cryptographic identity verification,
ensuring both authorization (who they are) and payload integrity (has the request been tampered with).
"""

from __future__ import annotations as _annotations

import asyncio
import time
from typing import Any

from starlette.responses import JSONResponse
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
            app: ASGI application (the next callable in the pipeline)
            auth_config: Hydra authentication configuration
        """
        super().__init__(app, auth_config)
        
        # In-memory cache to reduce network roundtrips to the Hydra Admin API.
        self._introspection_cache = {}  
        
        # Per-token asyncio locks. In a highly concurrent async environment, 
        # this prevents the "Thundering Herd" (Cache Stampede) problem where 
        # 100 concurrent requests for an expired token trigger 100 network calls.
        self._cache_locks = {}  
        
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Strict memory boundary for payload signature verification.
        # Prevents Out-Of-Memory (OOM) crashes if a client uploads massive files.
        self._max_body_size = 2 * 1024 * 1024  # 2 MB
        
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
        """Validate OAuth2 token using Hydra introspection.
        
        This method utilizes a double-checked locking pattern to safely handle
        high-concurrency scenarios without blocking the main event loop.
        """
        # Truncate the token for the cache key to save memory space
        cache_key = token[:50] 

        # 1. Fast Path: Lock-free read. 99% of requests will hit this and return immediately.
        cached = self._introspection_cache.get(cache_key)
        if cached and cached["expires_at"] > time.time():
            return cached["data"]

        # 2. Slow Path: Cache miss. Acquire a lock specifically for this token.
        lock = self._cache_locks.setdefault(cache_key, asyncio.Lock())
        
        async with lock:
            # Double-check inside the lock. Another asynchronous request might have
            # acquired the lock just before us and populated the cache.
            cached = self._introspection_cache.get(cache_key)
            if cached and cached["expires_at"] > time.time():
                return cached["data"]

            try:
                # Network I/O boundary: Reach out to the Hydra server
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

                # Populate the cache for subsequent requests
                expires_at = min(introspection_result["exp"], current_time + self._cache_ttl)
                self._introspection_cache[cache_key] = {
                    "data": introspection_result,
                    "expires_at": expires_at,
                }

                # Perform a lightweight cache sweep
                self._lazy_clean_cache()

                return introspection_result
            except Exception as e:
                logger.error(f"Token introspection failed: {e}")
                raise
              
    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize Hydra introspection data into a standard user/service object."""
        # Machine-to-Machine (M2M) tokens have a different lifecycle than user tokens.
        is_m2m = (
            token_payload.get("token_type") == "access_token"
            and token_payload.get("grant_type") == "client_credentials"
        )

        # Build the baseline authorization context
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

        # Hydrate with extended claims if this is a standard user token
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
        """O(1) amortized cache cleanup.
        
        Python dicts maintain insertion order. Because we insert tokens sequentially 
        over time, the oldest tokens are always at the start of the dict. We only 
        iterate until we hit the first unexpired token, avoiding a full O(N) scan.
        """
        current_time = time.time()
        expired_keys = []
        
        for key, value in self._introspection_cache.items():
            if value["expires_at"] <= current_time:
                expired_keys.append(key)
            else:
                # Early exit: If this token is still valid, all subsequent ones are too.
                break
                
        # Clean up both the cache payload and its associated lock
        for key in expired_keys:
            self._introspection_cache.pop(key, None)
            self._cache_locks.pop(key, None)
            
    async def _verify_did_signature(
        self, request: Any, client_did: str
    ) -> tuple[bool, dict[str, Any]]:
        """Verify the cryptographic integrity of the incoming request payload.
        
        Warning: This method consumes the request body stream and performs heavy CPU math.
        It is carefully engineered to not block the ASGI event loop or cause memory leaks.
        """
        signature_data = extract_signature_headers(dict(request.headers))

        # Backward compatibility for clients not yet using DID signing
        if not signature_data:
            return True, {"did_verified": False, "reason": "no_signature_headers"}

        # Ensure the token owner is actually the one who signed the payload
        if signature_data["did"] != client_did:
            return False, {"did_verified": False, "reason": "did_mismatch"}

        public_key = await get_public_key_from_hydra(client_did, self.hydra_client)
        if not public_key:
            return True, {"did_verified": False, "reason": "no_public_key"}

        # Memory Safety Guard: Reject payloads larger than our threshold before
        # attempting to load them into RAM for hashing.
        content_length = int(request.headers.get("content-length", 0))
        if content_length > self._max_body_size:
            logger.warning(f"Payload too large for signature verification: {content_length} bytes")
            return False, {"did_verified": False, "reason": "payload_too_large"}

        # ASGI Body Stream Management: 
        # Reading the body consumes the underlying network stream. If we don't
        # reconstruct it, the downstream route handler will hang forever waiting for data.
        body = await request.body()
        
        # Inject a mock receive function to "rewind" the stream for the next middleware
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive

        # CPU Bound Operations:
        # Cryptography is computationally heavy. We use asyncio.to_thread to run the 
        # verification in a background thread pool, keeping the main event loop 
        # responsive to other incoming network requests.
        is_valid = await asyncio.to_thread(
            verify_signature,
            body=body,
            signature=signature_data["signature"],
            did=signature_data["did"],
            timestamp=signature_data["timestamp"],
            public_key=public_key,
            max_age_seconds=300
        )

        if is_valid:
            return True, {"did_verified": True, "did": client_did, "timestamp": signature_data["timestamp"]}
        else:
            return False, {"did_verified": False, "reason": "invalid_signature", "did": client_did}
    
    async def dispatch(self, request, call_next):
        """The core middleware execution flow.
        
        Similar to `(req, res, next)` patterns, this intercepts the request,
        applies our business rules, and conditionally calls `call_next(request)`
        to pass control down the chain. 
        """
        path = request.url.path

        # 1. Route Bypass: Allow public health checks and open endpoints through
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            return await call_next(request)

        # 2. Extract Bearer Token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"No token provided for {path}")
            return await self._auth_required_error(request)

        # 3. Layer 1: Validate OAuth2 token against Hydra
        try:
            token_payload = await self._validate_token(token)
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            return self._handle_validation_error(e, path)

        # 4. Normalize the authenticated entity's data
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            from bindu.common.protocol.types import InvalidTokenError
            
            code, message = extract_error_fields(InvalidTokenError)
            return jsonrpc_error(code=code, message=message, status=401)

        # 5. Layer 2: Verify DID signature (if the client identity requires it)
        client_did = user_info.get("client_id")
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

            # Enrich the user context with the verification results
            user_info["signature_info"] = signature_info
            logger.debug(f"DID verification result: {signature_info}")

        # 6. Context Injection: Attach the resolved user object to the request state
        # so downstream controllers have access to `req.user`
        self._attach_user_context(request, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, "
            f"m2m={user_info.get('is_m2m', False)}, "
            f"did_verified={user_info.get('signature_info', {}).get('did_verified', False)}"
        )

        # 7. Pass control to the next middleware or final route handler
        return await call_next(request)

    def _handle_validation_error(self, error: Exception, path: str) -> Any:
        """Map raw exceptions to standard JSON-RPC error responses."""
        error_str = str(error).lower()

        # Differentiate between a down auth server vs an invalid client token
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

        # Fall back to base class error handling for unknown states
        return super()._handle_validation_error(error, path)