"""
Token Blacklist Service — Redis-backed token revocation for forced logout.

When a user logs out, changes their password, or an admin forces a session
revocation, the token's ``jti`` (JWT ID) is added to a Redis blacklist.
Every authenticated request checks the blacklist before proceeding.

If Redis is unavailable the blacklist degrades gracefully — tokens are
validated only by signature/expiry (the pre-existing behaviour).

Session management features:
- Concurrent session limiting (max N active sessions per user)
- IP-based anomaly detection (flags logins from new IPs)
"""

import logging
import time
from typing import Dict, Optional, List

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for blacklisted token JTIs
_BLACKLIST_PREFIX = "token:blacklist:"
_SESSION_PREFIX = "session:active:"
_IP_HISTORY_PREFIX = "user:ip_history:"

# Limits
MAX_CONCURRENT_SESSIONS = 5
MAX_IP_HISTORY = 20
MAX_MEMORY_BLACKLIST_SIZE = 10000


class TokenBlacklistService:
    """Redis-backed JWT blacklist for token revocation.

    Falls back to an in-memory dict when Redis is unavailable so that
    logout / token revocation still works (within a single process).
    The in-memory blacklist is bounded to MAX_MEMORY_BLACKLIST_SIZE entries
    and periodically cleaned of expired entries.
    """

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None
        self._enabled: bool = bool(settings.REDIS_URL)
        # In-memory fallback: jti -> expiry timestamp
        self._memory_blacklist: Dict[str, float] = {}
        self._last_cleanup: float = 0.0
        self._cleanup_interval: float = 60.0  # Clean up every 60 seconds at most

    async def connect(self) -> bool:
        """Connect to Redis. Returns True on success."""
        if not self._enabled:
            return False
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("Token blacklist service connected to Redis")
            return True
        except Exception as e:
            logger.warning("Token blacklist Redis connection failed: %s — revocation disabled", e)
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def _cleanup_memory_blacklist(self) -> None:
        """Remove expired entries from the in-memory blacklist.

        Also enforces MAX_MEMORY_BLACKLIST_SIZE by evicting the soonest-to-expire
        entries when the limit is exceeded. Runs at most once per cleanup interval.
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval and len(self._memory_blacklist) < MAX_MEMORY_BLACKLIST_SIZE:
            return
        self._last_cleanup = now
        # Remove expired entries
        self._memory_blacklist = {
            k: v for k, v in self._memory_blacklist.items() if v > now
        }
        # Enforce size limit by removing soonest-to-expire entries
        if len(self._memory_blacklist) > MAX_MEMORY_BLACKLIST_SIZE:
            sorted_entries = sorted(self._memory_blacklist.items(), key=lambda x: x[1])
            self._memory_blacklist = dict(sorted_entries[-MAX_MEMORY_BLACKLIST_SIZE:])

    async def revoke(self, jti: str, ttl: Optional[int] = None) -> bool:
        """Add a token JTI to the blacklist.

        Args:
            jti: The JWT ID (``jti`` claim) to revoke.
            ttl: Seconds until the entry expires from Redis. Defaults to
                 ``TOKEN_BLACKLIST_TTL_SECONDS`` from settings. Should be
                 >= the token's remaining lifetime.

        Returns:
            True if the token was successfully blacklisted.
        """
        if not jti:
            return False

        ttl = ttl or settings.TOKEN_BLACKLIST_TTL_SECONDS

        if self._client:
            try:
                await self._client.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl, "1")
                logger.info("Token revoked: jti=%s (ttl=%ds)", jti[:8] + "...", ttl)
                return True
            except Exception as e:
                logger.error("Failed to revoke token via Redis jti=%s: %s", jti[:8] + "...", e)
                # Fall through to in-memory fallback

        # In-memory fallback
        self._memory_blacklist[jti] = time.time() + ttl
        self._cleanup_memory_blacklist()
        logger.info("Token revoked (in-memory fallback): jti=%s (ttl=%ds)", jti[:8] + "...", ttl)
        return True

    async def is_revoked(self, jti: str) -> bool:
        """Check whether a token JTI has been revoked.

        Checks Redis first, then falls back to the in-memory blacklist.
        """
        if not jti:
            return False

        if self._client:
            try:
                result = await self._client.exists(f"{_BLACKLIST_PREFIX}{jti}")
                if bool(result):
                    return True
            except Exception as e:
                logger.warning("Blacklist check failed for jti=%s: %s — checking in-memory", jti[:8] + "...", e)

        # In-memory fallback check
        expiry = self._memory_blacklist.get(jti)
        if expiry is not None and expiry > time.time():
            return True
        return False

    async def revoke_all_for_user(self, user_id: str, jti_list: list[str]) -> int:
        """Revoke multiple tokens at once (e.g. on password change).

        Args:
            user_id: For logging purposes.
            jti_list: List of JTI strings to revoke.

        Returns:
            Number of tokens successfully revoked.
        """
        revoked = 0
        for jti in jti_list:
            if await self.revoke(jti):
                revoked += 1
        if revoked:
            logger.info("Bulk revocation for user=%s: %d/%d tokens revoked", user_id[:8] + "...", revoked, len(jti_list))
        return revoked

    # ------------------------------------------------------------------
    # Concurrent session management
    # ------------------------------------------------------------------

    async def register_session(
        self, user_id: str, jti: str, ttl: Optional[int] = None
    ) -> Optional[List[str]]:
        """Register a new session and enforce concurrent session limit.

        Stores the JTI in a sorted set keyed by user_id, scored by timestamp.
        If the user exceeds ``MAX_CONCURRENT_SESSIONS``, the oldest sessions
        are revoked automatically.

        Returns:
            List of evicted JTIs (empty if none), or None if Redis unavailable.
        """
        if not self._client or not jti:
            return None

        import time
        session_key = f"{_SESSION_PREFIX}{user_id}"
        ttl = ttl or settings.TOKEN_BLACKLIST_TTL_SECONDS
        now = time.time()

        try:
            # Add new session
            await self._client.zadd(session_key, {jti: now})
            await self._client.expire(session_key, ttl)

            # Prune expired sessions (score < now - ttl)
            await self._client.zremrangebyscore(session_key, "-inf", now - ttl)

            # Check count
            count = await self._client.zcard(session_key)
            evicted: List[str] = []

            if count > MAX_CONCURRENT_SESSIONS:
                # Evict oldest sessions (lowest scores)
                excess = count - MAX_CONCURRENT_SESSIONS
                oldest = await self._client.zrange(session_key, 0, excess - 1)
                for old_jti in oldest:
                    old_jti_str = old_jti.decode() if isinstance(old_jti, bytes) else old_jti
                    await self.revoke(old_jti_str, ttl)
                    evicted.append(old_jti_str)
                await self._client.zremrangebyrank(session_key, 0, excess - 1)
                logger.info(
                    "Session limit enforced for user=%s: evicted %d oldest sessions",
                    user_id[:8] + "...", len(evicted),
                )

            return evicted
        except Exception as e:
            logger.warning("Session registration failed for user=%s: %s", user_id[:8] + "...", e)
            return None

    async def remove_session(self, user_id: str, jti: str) -> None:
        """Remove a session on logout."""
        if not self._client or not jti:
            return
        try:
            await self._client.zrem(f"{_SESSION_PREFIX}{user_id}", jti)
        except Exception as e:
            logger.warning("Session removal failed: %s", e)

    async def get_active_session_count(self, user_id: str) -> int:
        """Return the number of active sessions for a user."""
        if not self._client:
            return 0
        try:
            return await self._client.zcard(f"{_SESSION_PREFIX}{user_id}") or 0
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # IP-based anomaly detection
    # ------------------------------------------------------------------

    async def record_login_ip(self, user_id: str, ip_address: str) -> bool:
        """Record login IP and detect anomalies.

        Maintains a set of known IPs per user. If the incoming IP has never
        been seen before, returns True (anomaly). Otherwise returns False.

        Gracefully degrades if Redis is unavailable (always returns False).
        """
        if not self._client or not ip_address:
            return False

        ip_key = f"{_IP_HISTORY_PREFIX}{user_id}"
        try:
            # Check if IP is already known
            is_known = await self._client.sismember(ip_key, ip_address)

            # Add to set
            await self._client.sadd(ip_key, ip_address)
            # Keep TTL refreshed (90 days)
            await self._client.expire(ip_key, 90 * 86400)

            # Trim to MAX_IP_HISTORY (best-effort — sets don't guarantee order,
            # but we only cap to prevent unbounded growth)
            count = await self._client.scard(ip_key)
            if count > MAX_IP_HISTORY:
                # Remove a random member (SPOP) to cap growth
                await self._client.spop(ip_key)

            if not is_known:
                logger.info(
                    "New IP detected for user=%s: %s (anomaly flag)",
                    user_id[:8] + "...", ip_address,
                )
                return True
            return False
        except Exception as e:
            logger.warning("IP anomaly check failed: %s", e)
            return False

    async def get_known_ips(self, user_id: str) -> List[str]:
        """Return all known IPs for a user."""
        if not self._client:
            return []
        try:
            members = await self._client.smembers(f"{_IP_HISTORY_PREFIX}{user_id}")
            return [m.decode() if isinstance(m, bytes) else m for m in members]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_blacklist: Optional[TokenBlacklistService] = None


async def get_token_blacklist() -> TokenBlacklistService:
    """Get or create the global token blacklist service."""
    global _blacklist
    if _blacklist is None:
        _blacklist = TokenBlacklistService()
        await _blacklist.connect()
    return _blacklist


async def shutdown_token_blacklist() -> None:
    """Disconnect the global blacklist instance during app shutdown."""
    global _blacklist
    if _blacklist is not None:
        await _blacklist.disconnect()
        _blacklist = None
