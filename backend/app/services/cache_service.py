"""
Cache Service - Redis-based caching for AI responses.

Caches AI-generated analysis *results* (never raw contract text) to reduce
API costs and improve response times for repeated analyses.

Security controls:
- Tenant isolation: all keys are prefixed with ``org:{org_id}:`` so that one
  organisation's cached data is never accessible to another.
- Only analysis result hashes and metadata are cached — full contract text
  is NEVER stored in Redis.
"""

import json
import hashlib
import logging
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum size (chars) for any single cached value — prevents accidental
# storage of large contract bodies.
_MAX_CACHE_VALUE_SIZE = 500_000


class CacheService:
    """
    Redis-based caching for AI analysis results.

    All cache keys are prefixed with ``org:{org_id}:`` to enforce tenant
    isolation at the cache layer.  Callers that omit *org_id* get the
    global ``org:__global__:`` namespace (suitable only for non-sensitive
    shared data such as feature flags).
    """

    def __init__(self) -> None:
        """Initialize cache service."""
        self._client: Optional[redis.Redis] = None
        self._enabled: bool = bool(settings.REDIS_URL)

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
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning("Redis connection failed: %s", e)
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._client is not None

    # ------------------------------------------------------------------
    # Tenant-aware key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tenant_key(key: str, org_id: Optional[str] = None) -> str:
        """Prefix *key* with the tenant namespace.

        Every cache key MUST pass through this method to guarantee tenant
        isolation.  If *org_id* is ``None`` the key lands in a shared
        global namespace that should only hold non-sensitive data.
        """
        ns = org_id or "__global__"
        return f"org:{ns}:{key}"

    # ------------------------------------------------------------------
    # Core get / set / delete — always tenant-scoped
    # ------------------------------------------------------------------

    async def get(self, key: str, *, org_id: Optional[str] = None) -> Optional[dict]:
        """
        Get cached value (tenant-scoped).

        Args:
            key: Logical cache key (will be prefixed with org namespace).
            org_id: Organisation ID for tenant isolation.

        Returns:
            Cached dict or None if not found/expired.
        """
        if not self._client:
            return None

        try:
            value = await self._client.get(self._tenant_key(key, org_id))
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
        ttl: int = 3600,
        *,
        org_id: Optional[str] = None,
    ) -> bool:
        """
        Set cached value (tenant-scoped).

        The serialised payload is checked against ``_MAX_CACHE_VALUE_SIZE``
        to prevent accidentally caching large contract bodies.

        Args:
            key: Logical cache key (will be prefixed with org namespace).
            value: Dict to cache — must be analysis results, **never** raw
                   contract text.
            ttl: Time-to-live in seconds.
            org_id: Organisation ID for tenant isolation.

        Returns:
            True if cached successfully.
        """
        if not self._client:
            return False

        try:
            serialised = json.dumps(value)
            if len(serialised) > _MAX_CACHE_VALUE_SIZE:
                logger.warning(
                    "Cache value too large (%d chars) — refusing to store. "
                    "Ensure only analysis results (not contract text) are cached.",
                    len(serialised),
                )
                return False
            await self._client.setex(
                self._tenant_key(key, org_id), ttl, serialised,
            )
            return True
        except Exception as e:
            logger.warning("Cache set error: %s", e)
            return False

    async def delete(self, key: str, *, org_id: Optional[str] = None) -> bool:
        """Delete a cached value (tenant-scoped)."""
        if not self._client:
            return False

        try:
            await self._client.delete(self._tenant_key(key, org_id))
            return True
        except Exception as e:
            logger.warning("Cache delete error: %s", e)
            return False

    async def delete_org_keys(self, org_id: str) -> int:
        """Delete ALL cached keys for an organisation (e.g. on org deletion).

        Uses SCAN to avoid blocking Redis with a single KEYS command.
        Returns the number of keys deleted.
        """
        if not self._client or not org_id:
            return 0

        deleted = 0
        try:
            pattern = f"org:{org_id}:*"
            batch: list = []
            async for key in self._client.scan_iter(match=pattern, count=200):
                batch.append(key)
                if len(batch) >= 200:
                    # Use pipeline for batch deletion
                    async with self._client.pipeline(transaction=False) as pipe:
                        for k in batch:
                            pipe.delete(k)
                        await pipe.execute()
                    deleted += len(batch)
                    batch = []
            # Flush remaining keys
            if batch:
                async with self._client.pipeline(transaction=False) as pipe:
                    for k in batch:
                        pipe.delete(k)
                    await pipe.execute()
                deleted += len(batch)
        except Exception as e:
            logger.warning("Cache delete_org_keys error: %s", e)
        return deleted

    # ------------------------------------------------------------------
    # Domain-specific key builders
    # ------------------------------------------------------------------

    @staticmethod
    def make_analysis_key(contract_hash: str, playbook_id: str) -> str:
        """
        Generate cache key for a full contract analysis result.

        Args:
            contract_hash: SHA-256 hash of the contract text (caller
                           computes this — the cache never sees raw text).
            playbook_id: Playbook identifier.

        Returns:
            Logical cache key (still needs tenant prefix via ``_tenant_key``).
        """
        return f"ai:analysis:{playbook_id}:{contract_hash[:24]}"

    @staticmethod
    def make_clause_key(clause_text: str, rule_id: str) -> str:
        """
        Generate cache key for per-clause AI analysis.

        Only the hash of the clause text is stored in the key — raw text
        never leaves the application process.
        """
        text_hash = hashlib.sha256(clause_text.encode()).hexdigest()[:16]
        return f"ai:clause:{rule_id}:{text_hash}"


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_cache: Optional[CacheService] = None


async def get_cache() -> CacheService:
    """Get or create cache service instance."""
    global _cache
    if _cache is None:
        _cache = CacheService()
        await _cache.connect()
    return _cache


async def shutdown_cache() -> None:
    """Disconnect the global cache instance during application shutdown."""
    global _cache
    if _cache is not None:
        await _cache.disconnect()
        _cache = None
