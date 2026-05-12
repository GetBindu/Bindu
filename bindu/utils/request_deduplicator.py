"""
Request deduplication and caching utilities for Bindu agents.

Prevents duplicate message processing by caching request signatures and results.
Useful for idempotent operations and handling retries.

Usage:
    from bindu.utils.request_deduplicator import RequestDeduplicator
    
    dedup = RequestDeduplicator(ttl_seconds=3600)
    
    # Generate unique request signature
    signature = await dedup.generate_signature(request_data)
    
    # Check if already processed
    cached_result = await dedup.get_cached_result(signature)
    if cached_result:
        return cached_result
    
    # Process request
    result = await process_request(request)
    
    # Cache the result
    await dedup.cache_result(signature, result)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.request_deduplicator")


@dataclass
class CacheEntry:
    """Cached request result."""
    result: Any
    """The cached result"""
    
    timestamp: float
    """When the result was cached"""
    
    ttl_seconds: float
    """Time to live for this entry"""
    
    hit_count: int = 0
    """Number of times this cached result has been used"""
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.timestamp > self.ttl_seconds


class SignatureGenerator:
    """Generates unique signatures for requests."""
    
    @staticmethod
    def generate_signature(
        data: Any,
        additional_fields: Optional[Dict[str, Any]] = None,
        hash_algorithm: str = 'sha256'
    ) -> str:
        """Generate a unique signature for request data.
        
        Args:
            data: Request data (will be converted to JSON)
            additional_fields: Optional additional fields to include in signature
            hash_algorithm: Hash algorithm to use (sha256, sha512, etc.)
            
        Returns:
            Unique signature string
        """
        try:
            # Convert data to JSON string for consistent hashing
            if isinstance(data, str):
                json_str = data
            else:
                json_str = json.dumps(data, sort_keys=True, default=str)
            
            # Add additional fields if provided
            if additional_fields:
                additional_json = json.dumps(
                    additional_fields,
                    sort_keys=True,
                    default=str
                )
                json_str = f"{json_str}:{additional_json}"
            
            # Generate hash
            hash_obj = hashlib.new(hash_algorithm)
            hash_obj.update(json_str.encode('utf-8'))
            
            return hash_obj.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to generate signature: {e}")
            # Return a fallback signature
            return hashlib.sha256(str(data).encode()).hexdigest()


class RequestDeduplicator:
    """
    Request deduplication cache for preventing duplicate processing.
    
    Caches request signatures and their results to handle retries
    and ensure idempotent operations.
    
    Example:
        dedup = RequestDeduplicator(ttl_seconds=3600)
        
        request_id = "msg-123"
        agent_id = "agent-456"
        
        cached = await dedup.get_cached_result(request_id, agent_id)
        if cached:
            return cached
        
        result = await process_request()
        await dedup.cache_result(request_id, result, agent_id)
    """
    
    def __init__(self, ttl_seconds: float = 3600):
        """Initialize deduplicator.
        
        Args:
            ttl_seconds: Time to live for cached entries (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._last_cleanup = time.time()
        self._max_cache_size = 10000
    
    async def generate_signature(
        self,
        request_data: Any,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate signature for request data.
        
        Args:
            request_data: Request payload
            additional_context: Additional context to include in signature
            
        Returns:
            Unique signature
        """
        return SignatureGenerator.generate_signature(
            request_data,
            additional_context
        )
    
    async def get_cached_result(self, signature: str) -> Optional[Any]:
        """Retrieve cached result for signature.
        
        Args:
            signature: Request signature
            
        Returns:
            Cached result if available and not expired, None otherwise
        """
        if signature not in self._cache:
            return None
        
        entry = self._cache[signature]
        
        if entry.is_expired:
            del self._cache[signature]
            return None
        
        # Update hit count
        entry.hit_count += 1
        logger.debug(
            f"Cache hit for signature {signature[:8]}... "
            f"(hit count: {entry.hit_count})"
        )
        
        return entry.result
    
    async def cache_result(
        self,
        signature: str,
        result: Any,
        ttl_seconds: Optional[float] = None
    ) -> None:
        """Cache result for signature.
        
        Args:
            signature: Request signature
            result: Result to cache
            ttl_seconds: Optional custom TTL for this entry
        """
        ttl = ttl_seconds or self.ttl_seconds
        
        entry = CacheEntry(
            result=result,
            timestamp=time.time(),
            ttl_seconds=ttl,
            hit_count=0
        )
        
        self._cache[signature] = entry
        
        # Cleanup if cache is getting too large
        if len(self._cache) > self._max_cache_size:
            await self._cleanup()
        
        logger.debug(
            f"Cached result for signature {signature[:8]}... "
            f"(TTL: {ttl}s)"
        )
    
    async def invalidate(self, signature: str) -> bool:
        """Invalidate cached result.
        
        Args:
            signature: Signature to invalidate
            
        Returns:
            True if entry was removed, False if not found
        """
        if signature in self._cache:
            del self._cache[signature]
            return True
        return False
    
    async def clear_all(self) -> int:
        """Clear all cached entries.
        
        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cached entries")
        return count
    
    async def _cleanup(self) -> None:
        """Remove expired entries and optimize cache."""
        current_time = time.time()
        expired_keys = []
        
        # Find expired entries
        for signature, entry in self._cache.items():
            if entry.is_expired:
                expired_keys.append(signature)
        
        # Remove expired entries
        for signature in expired_keys:
            del self._cache[signature]
        
        # If still over limit, remove least frequently used entries
        if len(self._cache) > self._max_cache_size:
            # Sort by hit count and remove least used
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].hit_count
            )
            
            to_remove = len(self._cache) - self._max_cache_size
            for signature, _ in sorted_items[:to_remove]:
                del self._cache[signature]
            
            logger.info(
                f"Cleaned up cache: removed {to_remove} entries, "
                f"cache size now {len(self._cache)}"
            )
        
        logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache stats including size, TTL, and hit count
        """
        total_hits = sum(e.hit_count for e in self._cache.values())
        average_hits = (
            total_hits / len(self._cache)
            if self._cache else 0
        )
        
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        
        return {
            "cache_size": len(self._cache),
            "expired_entries": expired,
            "total_hits": total_hits,
            "average_hits_per_entry": average_hits,
            "max_cache_size": self._max_cache_size,
            "ttl_seconds": self.ttl_seconds,
        }


class IdempotencyKeyManager:
    """
    Manages idempotency keys to ensure request idempotency.
    
    Tracks idempotency keys and ensures that duplicate requests
    with the same key are not processed twice.
    
    Example:
        manager = IdempotencyKeyManager()
        
        key = "idempotency-key-123"
        
        if await manager.is_processed(key):
            return await manager.get_response(key)
        
        response = await process_request()
        await manager.record_response(key, response)
    """
    
    def __init__(self, ttl_seconds: float = 86400):  # 24 hours default
        """Initialize idempotency key manager.
        
        Args:
            ttl_seconds: How long to track keys
        """
        self.ttl_seconds = ttl_seconds
        self._responses: Dict[str, tuple[Any, float]] = {}
    
    async def is_processed(self, idempotency_key: str) -> bool:
        """Check if idempotency key has been processed.
        
        Args:
            idempotency_key: The idempotency key
            
        Returns:
            True if already processed and not expired
        """
        if idempotency_key not in self._responses:
            return False
        
        response, timestamp = self._responses[idempotency_key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            del self._responses[idempotency_key]
            return False
        
        return True
    
    async def get_response(self, idempotency_key: str) -> Optional[Any]:
        """Get cached response for idempotency key.
        
        Args:
            idempotency_key: The idempotency key
            
        Returns:
            Cached response if exists and not expired
        """
        if not await self.is_processed(idempotency_key):
            return None
        
        response, _ = self._responses[idempotency_key]
        return response
    
    async def record_response(
        self,
        idempotency_key: str,
        response: Any
    ) -> None:
        """Record response for idempotency key.
        
        Args:
            idempotency_key: The idempotency key
            response: The response to cache
        """
        self._responses[idempotency_key] = (response, time.time())
        logger.debug(f"Recorded response for idempotency key {idempotency_key}")
    
    async def cleanup(self) -> int:
        """Remove expired idempotency records.
        
        Returns:
            Number of entries cleaned up
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._responses.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._responses[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired idempotency keys")
        
        return len(expired_keys)
