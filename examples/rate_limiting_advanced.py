"""
Example: Rate-limited and Deduplication-aware Bindu Agent

This example demonstrates how to use the advanced rate limiting and
request deduplication system to create a production-ready AI agent.

Features:
- Per-agent rate limiting
- Request deduplication for safety
- Idempotent payment operations
- Adaptive load scaling
"""

import asyncio
from bindu.penguin.bindufy import bindufy
from bindu.server.applications import BinduApplication
from bindu.server.middleware.rate_limit import (
    RateLimitMiddleware,
    RequestDeduplicationMiddleware,
    IdempotencyMiddleware,
)
from bindu.utils.rate_limiter import SlidingWindowLimiter, AdaptiveRateLimiter
from bindu.utils.request_deduplicator import RequestDeduplicator, IdempotencyKeyManager
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
import time


# ============================================================================
# Example 1: Simple Rate-Limited Agent
# ============================================================================

def create_rate_limited_agent():
    """Create a basic agent with rate limiting."""
    
    # Rate limit: 100 requests per minute per agent
    rate_limiter = SlidingWindowLimiter(max_requests=100, window_seconds=60)
    
    middleware = [
        Middleware(
            RateLimitMiddleware,
            limiter=rate_limiter,
            identifier_header="X-Agent-ID",
            excluded_paths=["/health", "/metrics"],
            status_code=429,
        )
    ]
    
    config = {
        "author": "example@agent.com",
        "name": "rate_limited_agent",
        "description": "An agent with rate limiting",
        "deployment": {"url": "http://localhost:3773", "expose": True},
        "skills": [],
    }
    
    def handler(messages: list[dict[str, str]]) -> dict:
        """Process messages."""
        return {
            "role": "assistant",
            "content": f"Processed {len(messages)} message(s)",
        }
    
    return config, handler, middleware


# ============================================================================
# Example 2: Agent with Request Deduplication
# ============================================================================

def create_deduplicated_agent():
    """Create an agent with request deduplication."""
    
    deduplicator = RequestDeduplicator(ttl_seconds=3600)
    
    middleware = [
        Middleware(
            RequestDeduplicationMiddleware,
            deduplicator=deduplicator,
            cache_ttl=3600,
            request_methods=["GET", "HEAD", "POST"],  # Cache POST too for idempotency
        )
    ]
    
    config = {
        "author": "example@agent.com",
        "name": "deduplicated_agent",
        "description": "An agent with request deduplication",
        "deployment": {"url": "http://localhost:3774", "expose": True},
        "skills": [],
    }
    
    def handler(messages: list[dict[str, str]]) -> dict:
        """Process messages with deduplication awareness."""
        return {
            "role": "assistant",
            "content": "Message processed and cached",
        }
    
    return config, handler, middleware


# ============================================================================
# Example 3: Agent with Idempotent Operations
# ============================================================================

def create_idempotent_payment_agent():
    """Create an agent that handles idempotent payment operations."""
    
    idempotency_manager = IdempotencyKeyManager(ttl_seconds=86400)
    
    middleware = [
        Middleware(
            IdempotencyMiddleware,
            key_manager=idempotency_manager,
            key_header="Idempotency-Key",
            enabled_methods=["POST", "PUT", "PATCH"],
        )
    ]
    
    config = {
        "author": "payment@agent.com",
        "name": "payment_agent",
        "description": "A payment processing agent with idempotency",
        "deployment": {"url": "http://localhost:3775", "expose": True},
        "skills": ["skills/payment-processing"],
    }
    
    # Simulate payment processing
    processed_payments = {}
    
    def handler(messages: list[dict[str, str]]) -> dict:
        """Process payment requests safely."""
        last_message = messages[-1]["content"]
        
        # The IdempotencyMiddleware will ensure that requests with the same
        # Idempotency-Key always get the same response, even if processed
        # multiple times. This is critical for payment operations.
        
        return {
            "role": "assistant",
            "content": f"Payment processed: {last_message}",
            "status": "completed",
        }
    
    return config, handler, middleware


# ============================================================================
# Example 4: Advanced Agent with Multiple Strategies
# ============================================================================

def create_advanced_agent():
    """Create an agent with rate limiting, dedup, and idempotency combined."""
    
    # Rate limiting: 200 requests per minute
    rate_limiter = SlidingWindowLimiter(max_requests=200, window_seconds=60)
    
    # Deduplication: 2-hour TTL
    deduplicator = RequestDeduplicator(ttl_seconds=7200)
    
    # Idempotency: 24-hour TTL for retry safety
    idempotency_manager = IdempotencyKeyManager(ttl_seconds=86400)
    
    middleware = [
        # Rate limiting comes first
        Middleware(
            RateLimitMiddleware,
            limiter=rate_limiter,
            identifier_header="X-Agent-ID",
            excluded_paths=["/health", "/metrics"],
        ),
        # Then deduplication
        Middleware(
            RequestDeduplicationMiddleware,
            deduplicator=deduplicator,
            cache_ttl=7200,
        ),
        # Finally idempotency for state-changing operations
        Middleware(
            IdempotencyMiddleware,
            key_manager=idempotency_manager,
            key_header="Idempotency-Key",
            enabled_methods=["POST", "PUT", "PATCH", "DELETE"],
        ),
    ]
    
    config = {
        "author": "advanced@agent.com",
        "name": "advanced_agent",
        "description": "Advanced agent with rate limiting and deduplication",
        "deployment": {"url": "http://localhost:3776", "expose": True},
        "skills": ["skills/analysis", "skills/data-processing"],
    }
    
    def handler(messages: list[dict[str, str]]) -> dict:
        """Handle messages with full protection."""
        return {
            "role": "assistant",
            "content": "Request processed with full safety guarantees",
        }
    
    return config, handler, middleware


# ============================================================================
# Example 5: Adaptive Load-Balancing Agent
# ============================================================================

def create_adaptive_agent():
    """Create an agent with adaptive rate limiting based on load."""
    
    # Starts at 50 req/s, scales between 10-100 req/s
    adapter = AdaptiveRateLimiter(
        initial_rate=50,
        min_rate=10,
        max_rate=100,
        adjustment_interval=30.0,  # Adjust every 30 seconds
    )
    
    config = {
        "author": "adaptive@agent.com",
        "name": "adaptive_agent",
        "description": "Agent with adaptive rate limiting",
        "deployment": {"url": "http://localhost:3777", "expose": True},
        "skills": [],
    }
    
    async def handler_async(messages: list[dict[str, str]]) -> dict:
        """Handle messages with adaptive rate limiting."""
        
        start_time = time.time()
        identifier = "adaptive-agent"
        
        try:
            # Check if allowed
            if not await adapter.is_allowed(identifier):
                return {
                    "error": "rate_limit_exceeded",
                    "message": "Adaptive limit exceeded",
                }
            
            # Simulate processing
            result = {
                "role": "assistant",
                "content": "Adaptively processed",
            }
            
            # Record metrics for adaptation
            response_time = time.time() - start_time
            success = True
            
            await adapter.record_request(
                identifier,
                response_time=response_time,
                success=success,
            )
            
            return result
            
        except Exception as e:
            # Record failure
            response_time = time.time() - start_time
            await adapter.record_request(
                identifier,
                response_time=response_time,
                success=False,
            )
            raise
    
    return config, handler_async, []


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    print("""
    ========================================
    Bindu Rate Limiting Examples
    ========================================
    
    This module demonstrates several examples of using the
    advanced rate limiting and deduplication system.
    
    Examples:
    1. Rate-limited agent (rate_limited_simple)
    2. Deduplicated agent (rate_limited_dedup)
    3. Payment agent with idempotency (payment_agent)
    4. Advanced multi-strategy agent (advanced_agent)
    5. Adaptive load-balancing agent (adaptive_agent)
    
    For a full working example with all features:
    
    from examples.rate_limiting_advanced import create_advanced_agent
    
    config, handler, middleware = create_advanced_agent()
    
    # Use the middleware with BinduApplication
    app = BinduApplication(
        middleware=middleware,
        ...
    )
    
    Or use with bindufy:
    
    bindufy(config, handler, middleware)
    """)


# ============================================================================
# Integration with BinduApplication
# ============================================================================

def example_full_integration():
    """Show how to integrate with BinduApplication."""
    
    from bindu.common.models import AgentManifest, DIDExtension
    
    # Create advanced agent setup
    config, handler, middleware = create_advanced_agent()
    
    # Create manifest
    manifest = AgentManifest(
        name=config["name"],
        description=config["description"],
        author=config["author"],
        deployment=config["deployment"],
        skills=config["skills"],
    )
    
    # Create application with middleware
    app = BinduApplication(
        manifest=manifest,
        middleware=middleware,
        auth_enabled=False,
        debug=False,
    )
    
    # Application now has:
    # - Rate limiting per agent
    # - Request deduplication
    # - Idempotent operation support
    # - Full safety guarantees
    
    return app


# ============================================================================
# Monitoring and Metrics
# ============================================================================

async def monitor_limiter_stats():
    """Example of monitoring rate limiter statistics."""
    
    dedup = RequestDeduplicator()
    
    # Simulate some activity
    await dedup.cache_result("sig-1", {"data": 1})
    await dedup.cache_result("sig-2", {"data": 2})
    await dedup.get_cached_result("sig-1")
    await dedup.get_cached_result("sig-1")
    
    # Get statistics
    stats = dedup.get_stats()
    
    print(f"""
    Cache Statistics:
    - Cache size: {stats['cache_size']}
    - Total hits: {stats['total_hits']}
    - Average hits per entry: {stats['average_hits_per_entry']:.2f}
    - TTL: {stats['ttl_seconds']} seconds
    """)


if __name__ == "__main__":
    # Run monitoring example
    # asyncio.run(monitor_limiter_stats())
    pass
