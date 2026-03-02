"""
Middleware for rate limiting and request deduplication.

Integrates rate limiting and deduplication strategies into the HTTP request pipeline.

Usage in application:
    from bindu.server.middleware.rate_limit import RateLimitMiddleware
    from bindu.utils.rate_limiter import SlidingWindowLimiter
    
    middleware = [
        Middleware(
            RateLimitMiddleware,
            limiter=SlidingWindowLimiter(max_requests=100, window_seconds=60)
        )
    ]
    
    app = BinduApplication(..., middleware=middleware)
"""

from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.utils.logging import get_logger
from bindu.utils.rate_limiter import RateLimiter, SlidingWindowLimiter
from bindu.utils.request_deduplicator import RequestDeduplicator, IdempotencyKeyManager
from bindu.utils.request_utils import get_client_ip

logger = get_logger("bindu.server.middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware for enforcing rate limits on requests.
    
    Prevents resource exhaustion by limiting request rates per client/agent.
    Supports multiple rate limiting strategies.
    
    Configuration:
        - limiter: RateLimiter instance (required)
        - identifier_header: Header to use for rate limit identifier (default: X-Agent-ID)
        - excluded_paths: List of paths to exclude from rate limiting
        - status_code: HTTP status code for rate limited responses (default: 429)
    """
    
    def __init__(
        self,
        app,
        limiter: RateLimiter | None = None,
        identifier_header: str = "X-Agent-ID",
        excluded_paths: list[str] | None = None,
        status_code: int = 429,
    ):
        """Initialize rate limit middleware.
        
        Args:
            app: ASGI application
            limiter: RateLimiter instance (defaults to SlidingWindowLimiter)
            identifier_header: Header name for rate limit identifier
            excluded_paths: Paths to exclude from rate limiting
            status_code: HTTP status code for rate limited responses
        """
        super().__init__(app)
        
        self.limiter = limiter or SlidingWindowLimiter(
            max_requests=100,
            window_seconds=60
        )
        self.identifier_header = identifier_header
        self.excluded_paths = excluded_paths or ["/health", "/metrics"]
        self.status_code = status_code
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get identifier for rate limiting
        identifier = self._get_identifier(request)
        
        # Check if request is allowed
        if not await self.limiter.is_allowed(identifier):
            remaining = 0
            reset_time = None
            
            # Try to get additional info from limiter
            if hasattr(self.limiter, 'get_remaining_requests'):
                remaining = self.limiter.get_remaining_requests(identifier)
            if hasattr(self.limiter, 'get_reset_time'):
                reset_time = self.limiter.get_reset_time(identifier)
            
            return JSONResponse(
                status_code=self.status_code,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "remaining": remaining,
                    "reset_in_seconds": reset_time,
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if hasattr(self.limiter, 'get_remaining_requests'):
            remaining = self.limiter.get_remaining_requests(identifier)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        if hasattr(self.limiter, 'get_reset_time'):
            reset_time = self.limiter.get_reset_time(identifier)
            if reset_time is not None:
                response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Extract identifier for rate limiting.
        
        Tries multiple sources in order of preference:
        1. X-Agent-ID header
        2. Authorization header
        3. Client IP address
        
        Args:
            request: HTTP request
            
        Returns:
            Unique identifier for rate limiting
        """
        # Try custom identifier header
        if self.identifier_header in request.headers:
            return request.headers[self.identifier_header]
        
        # Try authorization header (extract bearer token)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # "Bearer " is 7 chars
        
        # Fall back to IP address
        return get_client_ip(request)


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for preventing duplicate request processing.
    
    Caches request signatures and results to handle retries and
    ensure idempotent operations.
    
    Configuration:
        - deduplicator: RequestDeduplicator instance (required)
        - cache_ttl: TTL for cached results in seconds
        - request_methods: HTTP methods to cache (default: GET, HEAD)
        - enabled_for_paths: Paths to enable deduplication for
    """
    
    def __init__(
        self,
        app,
        deduplicator: RequestDeduplicator | None = None,
        cache_ttl: float = 3600,
        request_methods: list[str] | None = None,
        enabled_for_paths: list[str] | None = None,
    ):
        """Initialize deduplication middleware.
        
        Args:
            app: ASGI application
            deduplicator: RequestDeduplicator instance (auto-created if None)
            cache_ttl: TTL for cached results
            request_methods: HTTP methods to cache
            enabled_for_paths: Specific paths to enable dedup for
        """
        super().__init__(app)
        
        self.deduplicator = deduplicator or RequestDeduplicator(ttl_seconds=cache_ttl)
        self.cache_ttl = cache_ttl
        self.request_methods = request_methods or ["GET", "HEAD"]
        self.enabled_for_paths = enabled_for_paths
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with deduplication.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint
            
        Returns:
            HTTP response
        """
        # Only cache specific request methods
        if request.method not in self.request_methods:
            return await call_next(request)
        
        # Check if path is enabled for dedup (if specified)
        if self.enabled_for_paths:
            if request.url.path not in self.enabled_for_paths:
                return await call_next(request)
        
        # Generate request signature
        body = await request.body()
        signature = await self.deduplicator.generate_signature(
            {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "body": body.decode() if body else "",
            },
            {
                "client_ip": request.client.host if request.client else "unknown",
                "agent_id": request.headers.get("X-Agent-ID"),
            }
        )
        
        # Check if we have a cached result
        cached_result = await self.deduplicator.get_cached_result(signature)
        if cached_result:
            logger.debug(
                f"Returning cached response for {request.method} {request.url.path}"
            )
            cached_response, response_body = cached_result
            
            response = Response(
                content=response_body,
                status_code=cached_response["status_code"],
                headers=dict(cached_response["headers"]),
            )
            response.headers["X-Cache-Hit"] = "true"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code < 400:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            cached_response = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }
            
            await self.deduplicator.cache_result(
                signature,
                (cached_response, response_body),
                self.cache_ttl,
            )
            
            # Return response with cached body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        
        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling idempotent operations using idempotency keys.
    
    Expects an Idempotency-Key header and ensures that requests with the
    same key receive the same response, even if processed multiple times.
    
    Header: Idempotency-Key (required for POST/PUT/PATCH requests)
    Response: Idempotency-Key (echo back the key), Idempotency-Cached (true/false)
    """
    
    def __init__(
        self,
        app,
        key_manager: IdempotencyKeyManager | None = None,
        key_header: str = "Idempotency-Key",
        enabled_methods: list[str] | None = None,
    ):
        """Initialize idempotency middleware.
        
        Args:
            app: ASGI application
            key_manager: IdempotencyKeyManager instance (auto-created if None)
            key_header: Header name for idempotency key
            enabled_methods: HTTP methods to enforce idempotency for
        """
        super().__init__(app)
        
        self.key_manager = key_manager or IdempotencyKeyManager()
        self.key_header = key_header
        self.enabled_methods = enabled_methods or ["POST", "PUT", "PATCH", "DELETE"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with idempotency checking.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint
            
        Returns:
            HTTP response
        """
        # Only enforce for specific methods
        if request.method not in self.enabled_methods:
            return await call_next(request)
        
        # Get idempotency key
        idempotency_key = request.headers.get(self.key_header)
        
        # Key is optional, but if provided, enforce idempotency
        if not idempotency_key:
            return await call_next(request)
        
        # Check if this request was already processed
        if await self.key_manager.is_processed(idempotency_key):
            cached_response = await self.key_manager.get_response(idempotency_key)
            response_data, status_code, headers = cached_response
            
            logger.debug(
                f"Returning cached idempotent response for key {idempotency_key}"
            )
            
            response = JSONResponse(
                content=response_data,
                status_code=status_code,
                headers=headers,
            )
            response.headers["X-Idempotent-Cached"] = "true"
            response.headers[self.key_header] = idempotency_key
            
            return response
        
        # Process request
        response = await call_next(request)
        
        # Cache the response for idempotency
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        try:
            response_data = json_decode(response_body)
        except Exception:
            response_data = response_body.decode() if response_body else ""
        
        cached_response = (
            response_data,
            response.status_code,
            dict(response.headers),
        )
        
        await self.key_manager.record_response(idempotency_key, cached_response)
        
        # Return response with headers
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
        response.headers["X-Idempotent-Cached"] = "false"
        response.headers[self.key_header] = idempotency_key
        
        return response


def json_decode(data: bytes) -> dict:
    """Safely decode JSON from bytes."""
    import json
    return json.loads(data.decode())
