"""
Cache Utility Module

Provides Redis-based caching for frequently accessed data to improve performance.
"""

import json
import logging
import time
from functools import wraps
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.utils.metrics import REDIS_CONNECTED, record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages Redis-based caching for the application.

    Provides:
    - Key-value caching with TTL
    - Cache invalidation
    - Decorator for automatic function caching
    """

    # Cache key prefixes
    PREFIX_ANALYTICS = "cache:analytics:"
    PREFIX_CONTENT = "cache:content:"
    PREFIX_USER = "cache:user:"

    # Default TTLs in seconds
    TTL_SHORT = 60  # 1 minute
    TTL_MEDIUM = 300  # 5 minutes
    TTL_LONG = 3600  # 1 hour
    TTL_ANALYTICS = 120  # 2 minutes for analytics

    def __init__(self):
        """Initialize Redis connection pool"""
        self._redis: redis.Redis | None = None
        self._pool: redis.ConnectionPool | None = None
        self._sentinel: redis.Sentinel | None = None
        self._enabled = True
        self._last_connect_attempt: float = 0  # timestamp of last failed connect; enables 30s retry

    @staticmethod
    def _parse_sentinel_hosts(hosts_str: str) -> list[tuple[str, int]]:
        """Parse 'host1:port1,host2:port2' into [(host1, port1), (host2, port2)]."""
        result = []
        for entry in hosts_str.split(","):
            entry = entry.strip()
            if ":" in entry:
                host, port_str = entry.rsplit(":", 1)
                result.append((host.strip(), int(port_str.strip())))
            else:
                result.append((entry, 26379))
        return result

    async def connect(self) -> None:
        """Establish connection to Redis — supports Sentinel HA, redis_url, or individual params."""
        if self._redis is not None:
            return

        self._last_connect_attempt = time.time()

        # 1. Redis Sentinel (HA mode) — activated by REDIS_SENTINEL_HOSTS
        if settings.redis_sentinel_hosts:
            try:
                sentinel_hosts = self._parse_sentinel_hosts(settings.redis_sentinel_hosts)
                sentinel_kwargs: dict = {"decode_responses": True}
                if settings.redis_sentinel_password:
                    sentinel_kwargs["password"] = settings.redis_sentinel_password
                self._sentinel = redis.Sentinel(sentinel_hosts, **sentinel_kwargs)
                self._redis = self._sentinel.master_for(
                    settings.redis_sentinel_master_name,
                    decode_responses=True,
                )
                await self._redis.ping()
                REDIS_CONNECTED.labels(role="cache").set(1)
                logger.info(
                    "Cache: Connected to Redis via Sentinel (master=%s, sentinels=%s)",
                    settings.redis_sentinel_master_name,
                    sentinel_hosts,
                )
                return
            except Exception as sentinel_err:
                logger.warning("Cache: Sentinel connection failed (%s); falling back to standalone.", sentinel_err)
                self._sentinel = None
                self._redis = None

        # 2. Standalone — redis_url or individual params
        try:
            if settings.redis_url:
                self._pool = redis.ConnectionPool.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
            else:
                self._pool = redis.ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password,
                    decode_responses=True,
                )

            self._redis = redis.Redis(connection_pool=self._pool)
            await self._redis.ping()
            REDIS_CONNECTED.labels(role="cache").set(1)
            logger.info("Cache: Successfully connected to Redis")
        except Exception as e:
            REDIS_CONNECTED.labels(role="cache").set(0)
            logger.warning(f"Cache: Failed to connect to Redis: {e}. Caching disabled.")
            self._enabled = False

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None
        logger.info("Cache: Disconnected from Redis")

    async def _maybe_retry_connect(self) -> None:
        """Re-attempt connection after a 30-second cooldown to allow self-healing."""
        if not self._enabled and time.time() - self._last_connect_attempt >= 30:
            logger.info("Cache: retrying Redis connection after cooldown...")
            self._redis = None
            self._pool = None
            self._sentinel = None
            self._enabled = True  # reset so connect() proceeds
            await self.connect()

    async def get(self, key: str) -> Any | None:
        """
        Get a cached value by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        await self._maybe_retry_connect()
        if not self._enabled:
            return None

        try:
            if not self._redis:
                await self.connect()
            if not self._redis:
                return None

            data = await self._redis.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                record_cache_hit("redis")
                return json.loads(data)

            logger.debug(f"Cache MISS: {key}")
            record_cache_miss("redis")
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a cached value with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: TTL_MEDIUM)

        Returns:
            True if successful, False otherwise
        """
        await self._maybe_retry_connect()
        if not self._enabled:
            return False

        try:
            if not self._redis:
                await self.connect()
            if not self._redis:
                return False

            ttl = ttl or self.TTL_MEDIUM
            serialized = json.dumps(value, default=str)
            await self._redis.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled or not self._redis:
            return False

        try:
            await self._redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "cache:analytics:*")

        Returns:
            Number of keys deleted
        """
        if not self._enabled or not self._redis:
            return 0

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def invalidate_analytics(self) -> int:
        """Invalidate all analytics cache"""
        return await self.delete_pattern(f"{self.PREFIX_ANALYTICS}*")

    async def invalidate_content(self, content_id: int | None = None) -> int:
        """Invalidate content cache, optionally for specific content"""
        if content_id:
            await self.delete(f"{self.PREFIX_CONTENT}{content_id}")
            return 1
        return await self.delete_pattern(f"{self.PREFIX_CONTENT}*")

    async def invalidate_user(self, user_id: int | None = None) -> int:
        """Invalidate user cache, optionally for specific user"""
        if user_id:
            await self.delete(f"{self.PREFIX_USER}{user_id}")
            return 1
        return await self.delete_pattern(f"{self.PREFIX_USER}*")


# Global cache manager instance
cache_manager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """
    Dependency to get the cache manager instance.
    Ensures Redis connection is established.
    """
    if cache_manager._redis is None and cache_manager._enabled:
        await cache_manager.connect()
    return cache_manager


def cached(prefix: str, ttl: int = CacheManager.TTL_MEDIUM, key_builder: callable = None):
    """
    Decorator to cache async function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional function to build cache key from args

    Usage:
        @cached("analytics:dashboard", ttl=120)
        async def get_dashboard_data(db):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            cache_key = f"{prefix}:{key_builder(*args, **kwargs)}" if key_builder else prefix

            # Try to get from cache
            cm = await get_cache_manager()
            cached_value = await cm.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cm.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
