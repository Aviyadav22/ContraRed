"""
Cache Service - Redis-based caching for AI responses.

Caches AI-generated explanations and suggested fixes to reduce
API costs and improve response times for repeated clauses.
"""

import json
import hashlib
import logging
from typing import Optional, Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based caching for AI responses.
    
    Usage:
        cache = CacheService()
        await cache.connect()
        
        # Check cache
        cached = await cache.get("ai:clause:unlimited_liability:abc123")
        if cached:
            return cached
        
        # Store in cache
        await cache.set("ai:clause:unlimited_liability:abc123", result, ttl=3600)
    """
    
    def __init__(self):
        """Initialize cache service."""
        self._client: Optional[redis.Redis] = None
        self._enabled = bool(settings.REDIS_URL)
    
    async def connect(self) -> bool:
        """
        Connect to Redis.
        
        Returns:
            True if connected successfully, False otherwise.
        """
        if not self._enabled:
            return False
        
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning("Redis connection failed: %s", e)
            self._client = None
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._client is not None
    
    async def get(self, key: str) -> Optional[dict]:
        """
        Get cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached dict or None if not found/expired
        """
        if not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get error: %s", e)
            return None
    
    async def set(
        self,
        key: str,
        value: dict,
        ttl: int = 3600  # 1 hour default
    ) -> bool:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Dict to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if cached successfully
        """
        if not self._client:
            return False
        
        try:
            await self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning("Cache set error: %s", e)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        if not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete error: %s", e)
            return False
    
    @staticmethod
    def make_clause_key(clause_text: str, rule_id: str) -> str:
        """
        Generate cache key for AI clause analysis.
        
        Args:
            clause_text: The clause text
            rule_id: Rule identifier
            
        Returns:
            Cache key string
        """
        text_hash = hashlib.md5(clause_text.encode()).hexdigest()[:16]
        return f"ai:clause:{rule_id}:{text_hash}"


# Global cache instance
_cache: Optional[CacheService] = None


async def get_cache() -> CacheService:
    """Get or create cache service instance."""
    global _cache
    if _cache is None:
        _cache = CacheService()
        await _cache.connect()
    return _cache
